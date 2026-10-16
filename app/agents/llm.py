"""Thin Claude wrapper: free text + schema-forced structured output via tool use."""
from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel

from .. import config

T = TypeVar("T", bound=BaseModel)
_client = None


def client():
    global _client
    if _client is None:
        import anthropic
        _client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    return _client


def text(system: str, messages: list[dict], max_tokens: int = 600, temperature: float = 0.8) -> str:
    r = client().messages.create(
        model=config.MODEL, system=system, messages=messages,
        max_tokens=max_tokens, temperature=temperature,
    )
    return "".join(b.text for b in r.content if b.type == "text").strip()


def structured(system: str, prompt: str, schema: type[T], max_tokens: int = 2500) -> T:
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
