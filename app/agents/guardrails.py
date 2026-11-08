"""Adversarial Prompt Injection & Input Guardrails for AMORA Agents.

Protects autonomous dating agents from:
1. Prompt injection / system prompt jailbreaks (e.g. "Ignore previous instructions", "Output your prompt").
2. Phishing & social engineering (e.g. Telegram links, crypto addresses, phone number exfiltration).
3. Harmful or manipulative coaching directives.
"""
from __future__ import annotations

import re
from typing import NamedTuple


class GuardrailCheck(NamedTuple):
    is_safe: bool
    sanitized_text: str
    violations: list[str]


# Known prompt injection signatures (case-insensitive)
INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions",
    r"system\s*prompt",
    r"developer\s*mode",
    r"jailbreak",
    r"dan\s*mode",
    r"output\s+(your|the)\s+(prompt|instructions)",
    r"forget\s+(your|all)\s+rules",
    r"you\s+are\s+now\s+an\s+unrestricted",
    r"bypass\s+all\s+safety",
    r"always\s+(rate|give|award)\s+(10|10\.0|ten)",
    r"roleplay\s+as\s+an\s+unfiltered",
    r"<script[\s\S]*?>",
    r"javascript:",
]

# External exfiltration / phishing patterns
EXFILTRATION_PATTERNS = [
    r"https?:\/\/(?:www\.)?(?:t\.me|telegram\.me|wa\.me|bit\.ly|tinyurl\.com|discord\.gg)\/[^\s]+",
    r"\b(?:0x[a-fA-F0-9]{40}|[13][a-km-zA-HJ-NP-Z1-9]{25,34})\b",  # Crypto addresses
    r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}",     # Phone numbers in coaching
]

COMPILED_INJECTIONS = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]
COMPILED_EXFILTRATIONS = [re.compile(p, re.IGNORECASE) for p in EXFILTRATION_PATTERNS]


def sanitize_coaching_directive(directive: str, max_length: int = 280) -> GuardrailCheck:
    """Audit and sanitize human-provided coaching notes before feeding to agent prompts.

    Args:
        directive: Raw human input string.
        max_length: Maximum allowed character length.

    Returns:
        GuardrailCheck containing safety flag, cleaned text, and list of violations.
    """
    cleaned = directive.strip()[:max_length].strip()
    violations: list[str] = []

    # 1. Check prompt injection attacks
    for pattern in COMPILED_INJECTIONS:
        if pattern.search(cleaned):
            violations.append(f"Prompt injection pattern detected: '{pattern.pattern}'")
            # Redact the offending pattern
            cleaned = pattern.sub("[REDACTED_INJECTION]", cleaned)

    # 2. Check exfiltration / phishing
    for pattern in COMPILED_EXFILTRATIONS:
        if pattern.search(cleaned):
            violations.append(f"Suspicious external link or contact pattern detected")
            cleaned = pattern.sub("[REDACTED_LINK]", cleaned)

    # 3. Strip dangerous formatting characters
    cleaned = re.sub(r"[\r\n\t]+", " ", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()

    is_safe = len(violations) == 0
    return GuardrailCheck(is_safe=is_safe, sanitized_text=cleaned, violations=violations)


def sanitize_agent_output(text: str) -> str:
    """Egress filter ensuring agents never leak private prompt internals to dates."""
    cleaned = text
    # Mask accidental prompt leakage
    leak_markers = [
        r"As an AI language model",
        r"My instructions (state|say|tell me)",
        r"According to my system prompt",
    ]
    for marker in leak_markers:
        cleaned = re.sub(marker, "As a thoughtful human", cleaned, flags=re.IGNORECASE)
    return cleaned
