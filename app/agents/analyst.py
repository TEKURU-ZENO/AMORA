"""The Analyst agent: reads a person's two sources and writes their profile.

Reading is done in three visible passes, each logged to `reading_log` so the profile page
can show *how* the agent got to its conclusions:
  1. LinkedIn pass  -> career arc, work rhythm, values signalled by work
  2. Instagram pass -> hobbies, social energy, aesthetics, what they actually do with free time
  3. Cross-read     -> reconcile the two (the LinkedIn self vs the Instagram self), derive needs
Every claim on the profile carries an evidence snippet from one of the two sources.
"""
from __future__ import annotations

import re
from collections import Counter

from .. import config
from ..models import Analysis, Evidence, SourceBundle
from . import llm, validation
from .taxonomy import DEALBREAKER_RULES, TAXONOMY, TRAIT_TO_NEED, TRAIT_TO_VALUE, VENUES, DEFAULT_VENUE


SYSTEM = """You are a perceptive, kind matchmaking analyst representing ONE person.
You may use exactly two sources: their public LinkedIn and their public Instagram, given below.
Never invent facts that are not supported by these sources, never guess protected attributes
(religion, caste, health, sexuality, ethnicity) and never comment on looks or body.
Infer gently and say how confident you are. Write like a thoughtful friend, not marketing copy."""


def _li_text(b: SourceBundle) -> str:
    li = b.linkedin
    exp = "\n".join(f"- {e.title} @ {e.company} ({e.duration}): {e.description}" for e in li.experience)
    return (f"Name: {li.full_name}\nHeadline: {li.headline}\nLocation: {li.location}\nAbout: {li.about}\n"
            f"Experience:\n{exp}\nEducation: {', '.join(li.education)}\nSkills: {', '.join(li.skills)}\n"
            f"Volunteering: {', '.join(li.volunteering)}\nLanguages: {', '.join(li.languages)}")


def _ig_text(b: SourceBundle) -> str:
    ig = b.instagram
    posts = "\n".join(f"- [{p.kind}{' @ ' + p.location if p.location else ''}] {p.caption} {' '.join('#' + h for h in p.hashtags)}"
                      for p in ig.posts)
    return f"@{ig.username} ({ig.full_name})\nBio: {ig.bio}\nFollowers: {ig.followers}\nPosts:\n{posts}"


# ------------------------------------------------------------------ LLM engine

def _analyze_llm(b: SourceBundle, log: list[str]) -> Analysis:
    li_notes = llm.text(SYSTEM, [{"role": "user", "content":
        "PASS 1 / LinkedIn. Read this and write 5-8 terse reading notes about career arc, work rhythm, "
        "what they care about, and what this suggests for a relationship. Quote short snippets.\n\n" + _li_text(b)}],
        max_tokens=700, temperature=0.4)
    log.append("LinkedIn pass:\n" + li_notes)
    ig_notes = llm.text(SYSTEM, [{"role": "user", "content":
        "PASS 2 / Instagram. Read this and write 5-8 terse reading notes about hobbies, how they spend free time, "
        "social energy, recurring places/people/themes. Quote short snippets.\n\n" + _ig_text(b)}],
        max_tokens=700, temperature=0.4)
    log.append("Instagram pass:\n" + ig_notes)
    a = llm.structured(SYSTEM,
        "PASS 3 / Cross-read. Reconcile the LinkedIn self and the Instagram self. Where they disagree, say so in the "
        "summary. Derive NEEDS (what they need from a partner) from evidence, not stereotypes. Every evidence item "
        "must quote a real snippet from the sources.\n\n"
        f"LINKEDIN SOURCE\n{_li_text(b)}\n\nINSTAGRAM SOURCE\n{_ig_text(b)}\n\n"
        f"YOUR NOTES\n{li_notes}\n\n{ig_notes}", Analysis)
    log.append(f"Cross-read: {len(a.needs)} needs, {len(a.hobbies)} hobbies, {len(a.evidence)} evidence items, "
               f"confidence {a.confidence:.2f}")
    return a


# ------------------------------------------------------------------ offline engine

_KW = {label: [(k.lower(), re.compile(r"(?<![a-z0-9])" + re.escape(k.lower()) + r"(?:s|es|ing|ed)?(?![a-z0-9])"))
            for k in kws] for label, (_, kws, _) in TAXONOMY.items()}
# words that mean something else in a CV ("running a team", "book club", "cook up a plan")
_AMBIGUOUS_ON_LINKEDIN = {"run", "running", "club", "party", "book", "books", "cook", "explore", "series", "style"}


def _scan(text: str, src: str, hits: dict, ev: list[Evidence]):
    low = text.lower()
    for label, pats in _KW.items():
        for kw, pat in pats:
            if src == "linkedin" and kw in _AMBIGUOUS_ON_LINKEDIN:
                continue
            m = pat.search(low)
            if m:
                hits[label] = hits.get(label, 0) + (2 if src == "instagram" else 1)
                if not any(e.claim == label for e in ev):
                    i = m.start()
                    snip = text[max(0, i - 40): i + 60].strip()
                    ev.append(Evidence(claim=label, source=src, snippet=snip))
                break


def _analyze_offline(b: SourceBundle, log: list[str]) -> Analysis:
    li, ig = b.linkedin, b.instagram
    hits: dict[str, int] = {}
    ev: list[Evidence] = []

    li_chunks = [li.headline, li.about, *[f"{e.title} {e.company} {e.description}" for e in li.experience],
                 *li.skills, *li.volunteering]
    for c in li_chunks:
        _scan(c, "linkedin", hits, ev)
    li_hits = dict(hits)
    log.append("LinkedIn pass: read headline, about, %d roles, %d skills. Signals: %s" % (
        len(li.experience), len(li.skills), ", ".join(sorted(li_hits)) or "none"))

    for c in [ig.bio, *[p.caption + " " + " ".join(p.hashtags) for p in ig.posts]]:
        _scan(c, "instagram", hits, ev)
    ig_only = sorted(set(hits) - set(li_hits))
    log.append("Instagram pass: read bio and %d posts. New signals only visible on Instagram: %s" % (
        len(ig.posts), ", ".join(ig_only) or "none"))

    ranked = [k for k, _ in sorted(hits.items(), key=lambda kv: -kv[1])]
    hobbies = [k for k in ranked if TAXONOMY[k][0] == "hobby"][:6]
    interests = [k for k in ranked if TAXONOMY[k][0] == "interest"][:6]

    traits = Counter()
    for k in ranked:
        for t in TAXONOMY[k][2]:
            traits[t] += hits[k]
    n_roles = len(li.experience)
    if n_roles >= 4:
        traits["ambitious"] += 2
    if any(w in (li.about + li.headline).lower() for w in ["founder", "lead", "head of", "building"]):
        traits["driven"] += 2
    places = {p.location for p in ig.posts if p.location}
    if len(places) >= 4:
        traits["adventurous"] += 2
    top_traits = [t for t, _ in traits.most_common(6)]

    values = list(dict.fromkeys(TRAIT_TO_VALUE[t] for t in top_traits if t in TRAIT_TO_VALUE))[:4]
    needs = [TRAIT_TO_NEED[t] for t in top_traits if t in TRAIT_TO_NEED][:4]
    dealbreakers = [DEALBREAKER_RULES[t] for t in top_traits if t in DEALBREAKER_RULES][:3]
    social = "outgoing" if traits["social"] > traits["introspective"] + traits["homebody"] else (
        "selective / one-on-one" if traits["introspective"] or traits["homebody"] else "balanced")
    lifestyle = {
        "pace": "fast, ambitious" if traits["ambitious"] or traits["driven"] else "steady",
        "social energy": social,
        "weekends": "outdoors and moving" if traits["active"] or traits["outdoorsy"] else "slow and cozy" if traits["homebody"] else "mixed",
        "travel": f"{len(places)} distinct places on recent posts" if places else "not much on the grid",
    }
    first = (li.full_name or ig.full_name or ig.username).split()[0] if (li.full_name or ig.full_name or ig.username) else "They"
    job = li.experience[0] if li.experience else None
    role = f"{job.title} at {job.company}" if job else li.headline
    ideal = VENUES.get(hobbies[0] if hobbies else (interests[0] if interests else ""), DEFAULT_VENUE)
    mismatch = ""
    if ig_only:
        mismatch = (f" LinkedIn shows the professional; Instagram shows a different side: "
                    f"{', '.join(ig_only[:3]).lower()} never appear on the CV.")
    summary = (f"{first} is a {', '.join(top_traits[:3]) or 'thoughtful'} {role or 'professional'}"
               f"{' based in ' + li.location if li.location else ''}. Free time goes to "
               f"{', '.join(h.lower() for h in hobbies[:3]) or 'things the grid does not show much of'}.{mismatch}")
    signal = len(ev)
    a = Analysis(
        display_name=li.full_name or ig.full_name or ig.username,
        one_liner=f"{role} · {', '.join(hobbies[:2]) or 'quietly private'}",
        summary=summary,
        needs=needs or ["Someone patient enough to get to know them beyond what's online"],
        hobbies=hobbies, interests=interests, values=values or ["Kindness"],
        personality=top_traits[:5],
        lifestyle=lifestyle,
        communication_style=("Direct and idea-led" if traits["analytical"] else "Warm and expressive" if traits["expressive"]
                             else "Easygoing, playful" if traits["social"] else "Considered, takes time to open up"),
        green_flags=[f"Shows up consistently for {h.lower()}" for h in hobbies[:2]] + (
            ["Gives time to others"] if "Volunteering & social impact" in interests else []),
        dealbreakers=dealbreakers,
        ideal_date=ideal,
        conversation_starters=[f"Ask about {e.claim.lower()}: \"{e.snippet[:70]}\"" for e in ev[:3]],
        evidence=ev[:12],
        confidence=round(min(0.95, 0.35 + 0.05 * signal), 2),
    )
    log.append(f"Cross-read: top traits {top_traits[:4]}, derived {len(a.needs)} needs, confidence {a.confidence}")
    return a


class _Log(list):
    """A reading log that also reports each note as it is written, so the UI can stream the passes."""

    def __init__(self, on_note=None):
        super().__init__()
        self.on_note = on_note

    def append(self, note):
        super().append(note)
        if self.on_note:
            self.on_note(len(self) - 1, note)


def analyze(b: SourceBundle, on_note=None) -> tuple[Analysis, list[str], str]:
    log: list[str] = _Log(on_note)
    engine = "offline"
    fallback_occurred = False
    fallback_reason = None
    if config.llm_enabled():
        try:
            a = _analyze_llm(b, log)
            engine = "claude"
        except Exception as e:
            fallback_occurred = True
            fallback_reason = str(e)
            log.append(f"LLM analysis failed ({e}); falling back to offline engine")
            a = _analyze_offline(b, log)
    else:
        a = _analyze_offline(b, log)

    # Validate output grounding against source corpus
    a, warnings = validation.validate_analysis(a, b)
    a.engine_used = engine
    a.fallback_occurred = fallback_occurred
    a.fallback_reason = fallback_reason
    if warnings:
        log.append(f"Validation layer: {len(warnings)} notes ({'; '.join(warnings[:2])})")
    return a, log, engine

