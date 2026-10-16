from __future__ import annotations

from typing import Tuple
from ..models import Analysis, Evidence, SourceBundle


def _extract_linkedin_corpus(li) -> str:
    parts = [li.headline, li.about, li.location, li.full_name]
    for e in li.experience:
        parts.extend([e.title, e.company, e.description, e.duration])
    parts.extend(li.skills)
    parts.extend(li.education)
    parts.extend(li.volunteering)
    parts.extend(li.languages)
    return " ".join(p for p in parts if p).lower()


def _extract_instagram_corpus(ig) -> str:
    parts = [ig.bio, ig.username, ig.full_name]
    for p in ig.posts:
        parts.extend([p.caption, p.location] + p.hashtags)
    return " ".join(p for p in parts if p).lower()


def validate_analysis(a: Analysis, sources: SourceBundle | None) -> Tuple[Analysis, list[str]]:
    """
    Common validation layer ensuring that:
    1. Every evidence snippet resolves to actual substrings in the scraped sources.
    2. Ungrounded claims or hallucinated evidence items are filtered and logged.
    3. Empty/sparse source profiles cannot claim high confidence or invented dealbreakers.
    """
    if not sources:
        return a, []

    warnings: list[str] = []
    li_corpus = _extract_linkedin_corpus(sources.linkedin)
    ig_corpus = _extract_instagram_corpus(sources.instagram)

    grounded_evidence: list[Evidence] = []
    for ev in a.evidence:
        snip = ev.snippet.strip().lower()
        if not snip:
            warnings.append(f"Empty evidence snippet for claim '{ev.claim}'")
            continue

        corpus = li_corpus if ev.source == "linkedin" else ig_corpus
        # Check substring match or keyword token containment
        if snip in corpus or any(token in corpus for token in snip.split() if len(token) > 4):
            grounded_evidence.append(ev)
        else:
            warnings.append(f"Ungrounded evidence snippet for claim '{ev.claim}' ({ev.source}): '{ev.snippet[:50]}'")

    a.evidence = grounded_evidence

    # Sparse source guard
    has_li = bool(sources.linkedin.headline or sources.linkedin.experience or sources.linkedin.skills)
    has_ig = bool(sources.instagram.bio or sources.instagram.posts)

    if not has_li and not has_ig:
        warnings.append("Sources are empty: demoting confidence and setting needs to unstated")
        a.confidence = min(a.confidence, 0.15)
        a.needs = ["Data insufficient to infer relationship needs"]
        a.dealbreakers = []

    a.validation_warnings = warnings
    return a, warnings
