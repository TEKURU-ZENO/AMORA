"""The dating harness: ingest -> analyse -> screen -> date -> rank.

Screening ("swiping"): every agent looks at every other person's public card and asks out
its top SHORTLIST_K. A date happens if at least one side asks. This keeps cost linear-ish
while still letting every agent go on several real dates.
"""
from __future__ import annotations

import concurrent.futures as cf
from typing import Callable

from pydantic import BaseModel

from . import config, store
from .agents import analyst, llm
from .agents.compat import compute
from .agents.dater import go_on_date
from .models import DateRecord, InstagramData, LinkedInData, Person, SourceBundle
from .scrape import apify
from .scrape.links import normalize_instagram, normalize_linkedin, person_id

Progress = Callable[[str | dict], None]


def _print(msg) -> None:
    """Default progress for the CLI: log lines only; dict events are for the live web screens."""
    if isinstance(msg, str):
        print(msg)


# ------------------------------------------------------------- ingest + analyse

def _source_event(which: str, data) -> dict:
    """A compact view of what was scraped, for the reading screen."""
    if which == "linkedin":
        return {"type": "source", "which": which, "headline": data.headline, "about": data.about[:280],
                "location": data.location, "roles": [f"{e.title} @ {e.company}" for e in data.experience[:5]],
                "skills": data.skills[:8], "education": data.education[:2]}
    return {"type": "source", "which": which, "username": data.username, "bio": data.bio[:200],
            "n_posts": len(data.posts),
            "posts": [{"caption": p.caption[:120], "location": p.location, "tags": p.hashtags[:4]} for p in data.posts[:9]]}


def ingest(linkedin_url: str, instagram_url: str, consent: bool, progress: Progress = _print) -> Person:
    if not consent:
        raise ValueError("Consent is required: confirm you are this person or have their permission.")
    li_url, li_handle = normalize_linkedin(linkedin_url)
    ig_url, ig_handle = normalize_instagram(instagram_url)
    pid = person_id(li_handle, ig_handle)
    existing = store.get_person(pid)
    if existing and existing.status in ("scraped", "analyzed") and existing.sources:
        progress(f"[{pid}] using existing scraped sources from checkpoint")
        p = existing
        if p.status == "analyzed" and p.analysis:
            return p
        return analyse(p, progress)
    p = Person(id=pid, linkedin_url=li_url, instagram_url=ig_url, consent=True)
    store.save_person(p)

    try:
        # If one source fails we still build a profile from the other, with a warning on the page.
        # A private Instagram is a hard stop: the person has not made it public, so we don't read it.
        progress(f"[{pid}] scraping LinkedIn via Apify ({config.APIFY_LINKEDIN_ACTOR})")
        progress({"type": "scrape", "which": "linkedin"})
        try:
            li = apify.scrape_linkedin(li_url)
            progress(_source_event("linkedin", li))
        except apify.ScrapeError as e:
            li = LinkedInData(url=li_url)
            p.warnings.append(f"LinkedIn could not be read: {e}")
            progress({"type": "source_failed", "which": "linkedin", "error": str(e)})
        progress(f"[{pid}] scraping Instagram via Apify ({config.APIFY_INSTAGRAM_ACTOR})")
        progress({"type": "scrape", "which": "instagram"})
        try:
            ig = apify.scrape_instagram(ig_url, ig_handle)
            progress(_source_event("instagram", ig))
        except apify.PrivateProfile:
            raise
        except apify.ScrapeError as e:
            ig = InstagramData(url=ig_url, username=ig_handle)
            p.warnings.append(f"Instagram could not be read: {e}")
            progress({"type": "source_failed", "which": "instagram", "error": str(e)})
        if len(p.warnings) == 2:
            raise apify.ScrapeError("Neither LinkedIn nor Instagram could be read, so there is nothing to analyse.")
        p.sources = SourceBundle(linkedin=li, instagram=ig)
        p.status = "scraped"
        store.save_person(p)
        return analyse(p, progress)
    except Exception as e:
        p.status, p.error = "error", str(e)
        store.save_person(p)
        raise


def ingest_demo(pid: str, li: LinkedInData, ig: InstagramData, progress: Progress = _print) -> Person:
    """Demo mode only: add a fictional persona without scraping, then analyse it like anyone else."""
    if not config.demo_mode():
        raise ValueError("Fictional personas are only allowed in demo mode (AGENTDATE_DEMO=1).")
    p = Person(id=pid, linkedin_url=li.url, instagram_url=ig.url, consent=True, synthetic=True,
               sources=SourceBundle(linkedin=li, instagram=ig), status="scraped")
    store.save_person(p)
    return analyse(p, progress)


def add_demo_personas(progress: Progress = _print) -> int:
    """Demo mode only: put the 25 fictional personas in the pool (skipping any already there)."""
    from scripts.synthetic import build
    added = 0
    for pid, li, ig in build():
        if store.get_person(pid):
            continue
        progress(f"adding demo persona {li.full_name}")
        ingest_demo(pid, li, ig, progress)
        added += 1
    progress(f"{added} demo personas added")
    return added


def analyse(p: Person, progress: Progress = _print) -> Person:
    progress(f"[{p.id}] analyst agent reading both sources")
    a, log, engine = analyst.analyze(p.sources, on_note=lambda i, note: progress({"type": "pass", "i": i, "text": note}))
    p.analysis, p.reading_log, p.status = a, [f"engine: {engine}", *log], "analyzed"
    store.save_person(p)
    progress(f"[{p.id}] profile ready: {a.one_liner}")
    return p


# ------------------------------------------------------------- screening

class SwipePick(BaseModel):
    id: str
    why: str


class Swipes(BaseModel):
    picks: list[SwipePick]


def screen(people: list[Person], askers: list[Person] | None = None) -> dict[str, list[tuple[str, str]]]:
    """Return {person_id: [(other_id, why), ...]} = who each agent asks out (all of `people`, or just `askers`)."""
    asks: dict[str, list[tuple[str, str]]] = {}
    for p in askers or people:
        others = [o for o in people if o.id != p.id]
        priors = sorted(((compute(p.analysis, o.analysis).prior, o) for o in others), key=lambda t: -t[0])
        picks = None
        if config.llm_enabled():
            try:
                cards = "\n".join(f"- id={o.id}: {o.analysis.one_liner}; hobbies {o.analysis.hobbies[:4]}; "
                                  f"interests {o.analysis.interests[:4]}; values {o.analysis.values[:3]}" for o in others)
                s = llm.structured(
                    f"You are the dating agent for {p.analysis.display_name}. Brief: needs {p.analysis.needs}; "
                    f"hobbies {p.analysis.hobbies}; values {p.analysis.values}; dealbreakers {p.analysis.dealbreakers}.",
                    f"Here are everyone's public cards. Ask out the {config.SHORTLIST_K} people most likely to be "
                    f"good for your human (not just similar). Use ids exactly.\n{cards}", Swipes, max_tokens=1200)
                valid = {o.id for o in others}
                picks = [(x.id, x.why) for x in s.picks if x.id in valid][: config.SHORTLIST_K]
            except Exception:
                picks = None
        if not picks:
            picks = []
            for prior, o in priors[: config.SHORTLIST_K]:
                c = compute(p.analysis, o.analysis)
                why = (f"shared {', '.join((c.shared_hobbies + c.shared_interests)[:2]).lower()}"
                       if c.shared_hobbies or c.shared_interests else "complementary energy")
                picks.append((o.id, f"{why} (prior {prior:.1f})"))
        asks[p.id] = picks
    return asks


# ------------------------------------------------------------- dating round

def _first(p: Person) -> str:
    return p.analysis.display_name.split()[0]


def date_tile(d: DateRecord, by_id: dict[str, Person]) -> dict:
    """What the dating floor needs to draw one date tile."""
    return {"id": d.id, "a": d.a, "b": d.b, "venue": d.venue, "mutual": d.mutual,
            "yes_a": d.verdict_a.second_date, "yes_b": d.verdict_b.second_date,
            "lines": [[_first(by_id[t.speaker]) if t.speaker in by_id else "", t.text[:110]] for t in d.turns]}


def run_round(progress: Progress = _print, only: str | None = None) -> list[DateRecord]:
    """A full round, or with `only`, just that person's agent asking out the existing pool
    (a new joiner dates everyone, demo personas included, without redoing anyone else's dates)."""
    people = [p for p in store.list_persons() if p.status == "analyzed" and p.analysis]
    if len(people) < 2:
        raise ValueError("Need at least two analysed people to start dating.")
    by_id = {p.id: p for p in people}
    if only and only not in by_id:
        raise ValueError("That profile isn't ready to date yet.")
    progress(f"{len(people)} agents in the pool" + (f"; {by_id[only].analysis.display_name}'s agent is going out" if only else ""))
    progress({"type": "phase", "phase": "screening", "people": len(people)})
    fresh = screen(people, askers=[by_id[only]] if only else None)
    if only:  # keep everyone else's asks and dates; replace this person's
        asks = {k: v for k, v in (store.get_meta("asks", {}) or {}).items() if k != only} | fresh
    else:
        asks = fresh
    store.set_meta("asks", asks)
    for pid, picks in fresh.items():
        progress({"type": "asks", "from": pid, "picks": [{"id": o, "why": w} for o, w in picks]})
    pairs = set()
    for pid, picks in fresh.items():
        for oid, _ in picks:
            pairs.add(tuple(sorted((pid, oid))))
    progress(f"screening done: {sum(len(v) for v in fresh.values())} invitations -> {len(pairs)} dates")
    progress({"type": "phase", "phase": "dating", "dates": len(pairs)})
    if only:
        store.clear_dates(only)
    else:
        store.clear_dates()
    out = []

    def one(pair):
        ida, idb = pair
        # the inviter goes first (whoever asked; if mutual, alphabetical)
        if ida not in [o for o, _ in asks.get(idb, [])] and idb in [o for o, _ in asks.get(ida, [])]:
            pass
        elif idb in [o for o, _ in asks.get(ida, [])]:
            pass
        else:
            ida, idb = idb, ida
        progress({"type": "date_start", "a": ida, "b": idb})
        return go_on_date(ida, by_id[ida].analysis, idb, by_id[idb].analysis)

    workers = config.MAX_PARALLEL_DATES if config.llm_enabled() else 1
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        for d in ex.map(one, sorted(pairs)):
            store.save_date(d)
            out.append(d)
            na, nb = by_id[d.a].analysis.display_name, by_id[d.b].analysis.display_name
            progress(f"date: {na} x {nb} at {d.venue} -> mutual {d.mutual:.1f}")
            progress({"type": "date_done", **date_tile(d, by_id)})
    progress({"type": "phase", "phase": "verdicts",
              "mutual_yes": sum(d.verdict_a.second_date and d.verdict_b.second_date for d in out)})
    store.set_meta("rankings", compute_rankings())
    progress("rankings computed")
    progress({"type": "phase", "phase": "rankings"})
    return out


# ------------------------------------------------------------- rankings

def compute_rankings() -> dict[str, list[dict]]:
    people = [p for p in store.list_persons() if p.analysis]
    dates = store.list_dates()
    idx: dict[tuple[str, str], DateRecord] = {}
    for d in dates:
        idx[(d.a, d.b)] = d
        idx[(d.b, d.a)] = d
    result: dict[str, list[dict]] = {}
    for p in people:
        rows = []
        for o in people:
            if o.id == p.id:
                continue
            d = idx.get((p.id, o.id))
            if d:
                mine = d.verdict_a if d.a == p.id else d.verdict_b
                theirs = d.verdict_b if d.a == p.id else d.verdict_a
                fit = 0.6 * mine.score + 0.4 * theirs.score - (1.0 if mine.dealbreaker_hit else 0)
                rows.append(dict(id=o.id, fit=round(max(0, fit), 2), dated=True, date_id=d.id,
                                 mutual_yes=mine.second_date and theirs.second_date,
                                 my_agent=mine.score, their_agent=theirs.score,
                                 why=mine.reasons[:2],
                                 assessment_status="dated",
                                 uncertainty="low (evaluated in date conversation)"))
            else:
                prior = compute(p.analysis, o.analysis).prior
                rows.append(dict(id=o.id, fit=round(0.55 * prior, 2), dated=False, date_id=None,
                                 mutual_yes=False, my_agent=None, their_agent=None,
                                 why=["Screened out before a date"],
                                 assessment_status="unassessed_prior",
                                 uncertainty="high (heuristic prior; unassessed in date)"))

        rows.sort(key=lambda r: (-r["fit"], r["id"]))
        for i, r in enumerate(rows, 1):
            r["rank"] = i
        result[p.id] = rows
    return result
