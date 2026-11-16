"""Thin LLM wrapper: Claude & Ollama for free text + schema-forced structured output."""
from __future__ import annotations

import json
import logging
import re
import urllib.request
from typing import TypeVar

from pydantic import BaseModel

from .. import config

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)
_client = None


def client():
    global _client
    if _client is None:
        import anthropic
        _client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    return _client


def _clean_json_str(s: str) -> str:
    s = s.strip()
    if s.startswith("```json"):
        s = s[7:]
    elif s.startswith("```"):
        s = s[3:]
    if s.endswith("```"):
        s = s[:-3]
    return s.strip()


def _ollama_chat(
    messages: list[dict],
    format_schema: dict | None = None,
    max_tokens: int = 1000,
    temperature: float = 0.5,
) -> str:
    payload: dict = {
        "model": config.OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
        },
    }
    if format_schema:
        payload["format"] = format_schema

    req = urllib.request.Request(
        f"{config.OLLAMA_HOST}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        return res["message"]["content"]


def text(system: str, messages: list[dict], max_tokens: int = 600, temperature: float = 0.8) -> str:
    if config.llm_provider() == "ollama":
        all_msgs = [{"role": "system", "content": system}] + messages
        return _ollama_chat(all_msgs, max_tokens=max_tokens, temperature=temperature).strip()

    r = client().messages.create(
        model=config.MODEL, system=system, messages=messages,
        max_tokens=max_tokens, temperature=temperature,
    )
    return "".join(b.text for b in r.content if b.type == "text").strip()


def structured(system: str, prompt: str, schema: type[T], max_tokens: int = 2500) -> T:
    if config.llm_provider() == "ollama":
        all_msgs = [
            {"role": "system", "content": f"{system}\nYou MUST output valid JSON conforming exactly to the requested schema."},
            {"role": "user", "content": prompt},
        ]
        raw_text = _ollama_chat(all_msgs, format_schema=schema.model_json_schema(), max_tokens=max_tokens, temperature=0.3)
        clean = _clean_json_str(raw_text)
        try:
            return schema.model_validate_json(clean)
        except Exception:
            # Attempt to extract outermost JSON object/array
            m = re.search(r"(\{.*\}|\[.*\])", clean, re.DOTALL)
            if m:
                try:
                    return schema.model_validate_json(m.group(0))
                except Exception:
                    pass
            logger.warning(f"Ollama JSON parse error on {schema.__name__}: raw={raw_text[:200]}")
            raise RuntimeError(f"Ollama failed to return valid {schema.__name__} structured JSON")

    tool = {
        "name": "submit",
        "description": f"Submit the {schema.__name__}.",
        "input_schema": schema.model_json_schema(),
    }
    r = client().messages.create(
        model=config.MODEL, system=system, max_tokens=max_tokens, temperature=0.4,
        tools=[tool], tool_choice={"type": "tool", "name": "submit"},
        messages=[{"role": "user", "content": prompt}],
    )
    for b in r.content:
        if b.type == "tool_use":
            return schema.model_validate(b.input)
    raise RuntimeError("model did not return structured output")
