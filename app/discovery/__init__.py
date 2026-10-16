"""Autonomous candidate discovery subsystem.

Components:
- search.py: Search engine integration for finding candidate LinkedIn profiles
- pairing.py: Finds candidate Instagram profiles
- verification.py: Strict identity verification enforcing direct cross-links
- registry.py: Candidate persistence, invitation tokens, rejection logging
- orchestrator.py: Coordinates batch discovery with rate limits and deduplication
"""
from . import models, orchestrator, pairing, registry, search, verification

__all__ = ["models", "orchestrator", "pairing", "registry", "search", "verification"]

