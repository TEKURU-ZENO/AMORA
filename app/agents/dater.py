"""The Dating agents.

Each person is represented by one agent that holds a PRIVATE brief (that person's analysis,
needs and dealbreakers). Two agents go on a date at a venue the inviting agent picks from
shared interests. They talk in turns; every turn has a public line and a private thought
(the agent's running read of whether this is good for its human). After the date each
agent independently files a Verdict to its own human. Agents never see the other side's
private brief or verdict.
"""
from __future__ import annotations

import hashlib
import random

from pydantic import BaseModel, Field

from .. import config
from ..models import Analysis, DateRecord, Turn, Verdict
from . import llm
from .compat import Compat, compute
from .taxonomy import DEFAULT_VENUE, VENUES


def first(a: Analysis) -> str:
    return a.display_name.split()[0]


def pick_venue(a: Analysis, b: Analysis, c: Compat) -> tuple[str, str]:
    for k in c.shared_hobbies + c.shared_interests:
        if k in VENUES:
            return VENUES[k], f"Both are into {k.lower()}"
    for k in a.hobbies + a.interests:
        if k in VENUES and k in (b.hobbies + b.interests):
            return VENUES[k], f"Both are into {k.lower()}"
    if b.hobbies and b.hobbies[0] in VENUES:
        return VENUES[b.hobbies[0]], f"{first(a)}'s agent picked something {first(b)} loves ({b.hobbies[0].lower()})"
    return DEFAULT_VENUE, "No strong shared activity, so somewhere easy to talk"


# =================================================================== LLM engine

class AgentTurn(BaseModel):
    thought: str = Field(description="Private read for your own human: what you just learned, what to probe next")
    say: str = Field(description="What you say out loud on the date, 1-3 sentences, in character as your human")


def _brief(me: Analysis) -> str:
    return (f"Name: {me.display_name}\nSummary: {me.summary}\nNeeds: {me.needs}\nHobbies: {me.hobbies}\n"
            f"Interests: {me.interests}\nValues: {me.values}\nPersonality: {me.personality}\n"
            f"Lifestyle: {me.lifestyle}\nCommunication: {me.communication_style}\nDealbreakers: {me.dealbreakers}")


def _card(other: Analysis) -> str:
    # what an agent can see of the other person before the date: their public profile card
    return f"{other.display_name}: {other.one_liner}. Hobbies {other.hobbies[:4]}, interests {other.interests[:4]}."


def _agent_system(me: Analysis, other: Analysis, venue: str) -> str:
    return (f"You are the dating agent for {me.display_name}. You go on this date ON THEIR BEHALF and speak "
            f"as them, grounded strictly in the brief below. Your job is to find out, honestly, whether "
            f"{first(other)} is good for {first(me)}: probe their needs and your human's dealbreakers, share "
            f"real things about your human, be warm and natural, never invent facts beyond the brief. "
            f"Do not oversell. Never discuss looks.\n\nPRIVATE BRIEF\n{_brief(me)}\n\n"
            f"WHAT YOU KNOW ABOUT YOUR DATE (their public card)\n{_card(other)}\n\nVENUE: {venue}")


PHASES = ["arriving, opening line", "small talk about the venue", "ask about something on their card",
          "share something real about your human", "probe what they need from a partner",
          "test one of your human's dealbreakers, gently", "find common ground or name a difference honestly",
          "talk about what a normal week looks like", "light, fun moment", "wrap up, hint whether you'd meet again"]


def _date_llm(a: Analysis, b: Analysis, ida: str, idb: str, venue: str) -> list[Turn]:
    turns: list[Turn] = []
    agents = [(ida, a, b), (idb, b, a)]
    for i in range(config.DATE_TURNS):
        pid, me, other = agents[i % 2]
        transcript = "\n".join(f"{first(a) if t.speaker == ida else first(b)}: {t.text}" for t in turns) or "(date just started)"
        phase = PHASES[min(i, len(PHASES) - 1)]
        out = llm.structured(_agent_system(me, other, venue),
                             f"Conversation so far:\n{transcript}\n\nYour turn ({phase}).", AgentTurn, max_tokens=500)
        turns.append(Turn(speaker=pid, text=out.say.strip(), thought=out.thought.strip()))
    return turns


def _verdict_llm(me: Analysis, other: Analysis, pid: str, turns: list[Turn], ida: str, venue: str) -> Verdict:
    transcript = "\n".join(f"{'YOU' if t.speaker == pid else first(other)}: {t.text}" for t in turns)
    thoughts = "\n".join(t.thought for t in turns if t.speaker == pid)
    v = llm.structured(_agent_system(me, other, venue),
        f"The date is over. Transcript:\n{transcript}\n\nYour private notes during the date:\n{thoughts}\n\n"
        f"File your verdict to {first(me)}. Be honest, calibrated (most dates are 4-7), and specific. "
        f"score = overall fit for {first(me)}. report_to_human is 2-3 sentences addressed to {first(me)}.",
        Verdict, max_tokens=800)
    v.agent_for = pid
    return v


# =================================================================== offline engine

def _rng(ida: str, idb: str) -> random.Random:
    return random.Random(int(hashlib.sha1(f"{min(ida, idb)}|{max(ida, idb)}".encode()).hexdigest()[:8], 16))


def _ev(a: Analysis, claim_pool: list[str]) -> tuple[str, str] | None:
    for e in a.evidence:
        if e.claim in claim_pool:
            return e.claim, e.snippet
    return (a.evidence[0].claim, a.evidence[0].snippet) if a.evidence else None


def _date_offline(a: Analysis, b: Analysis, ida: str, idb: str, venue: str, c: Compat) -> list[Turn]:
    r = _rng(ida, idb)
    A, B = first(a), first(b)
    shared = c.shared_hobbies + c.shared_interests
    T: list[Turn] = []

    def say(pid, text, thought):
        T.append(Turn(speaker=pid, text=text, thought=thought))

    opener = r.choice(["Hey, you must be {B}! I hope {v} sounded okay to you.",
                       "{B}? Hi! Glad you said yes to {v}.",
                       "Hi {B}, I'm {A}. Fair warning, I picked {v} so blame me if it's a disaster."])
    say(ida, opener.format(A=A, B=B, v=venue),
        f"Picked {venue} because {('we share ' + shared[0].lower()) if shared else 'it is easy to talk there'}. "
        f"Watching for: {', '.join(a.needs[:1]).lower() or 'general warmth'}.")

    b_top = (b.hobbies + b.interests + ["meeting new people"])[0]
    say(idb, r.choice([f"It's perfect actually. Anything with {b_top.lower()} energy and I'm in.",
                       f"Honestly great choice. I've been meaning to do more of this, {b_top.lower()} has taken over my weekends lately.",
                       f"Ha, no, it's a good call. I'm a {b.communication_style.lower().split(',')[0]} kind of person, this works."]),
        f"First impression: {A} thought about the venue. {'Promising, we overlap on ' + ', '.join(shared[:2]).lower() if shared else 'Not much overlap on paper, need to dig.'}")

    eb = _ev(b, shared or b.hobbies + b.interests)
    if eb:
        claim, snip = eb
        say(ida, f"Okay I have to ask, I saw something about {claim.lower()}. \"{snip[:60].strip()}...\" What's the story there?",
            f"Using a real thread from {B}'s profile rather than generic questions.")
        say(idb, r.choice([f"Oh, that! It's become a big part of who I am. It's where I switch off from work, and honestly where most of my friends come from.",
                           f"Ha, you did your homework. It started as a one-off and now I plan my weeks around it.",
                           f"That's my reset button. Work is {(b.lifestyle or {}).get('pace', 'busy')}, so I need something that's just mine."]) +
            f" What about you, what does your free time actually look like?",
            f"{A} asked about something I care about. Good sign for curiosity.")
    else:
        say(ida, f"So tell me something that's not on your LinkedIn.", "Thin profile on their side, opening it up.")
        say(idb, "I'm more interesting offline, I promise. What about you?", "Deflected a little.")

    a_top = (a.hobbies + ["work, if I'm honest"])[0]
    say(ida, f"Mostly {a_top.lower()}{', and ' + a.hobbies[1].lower() if len(a.hobbies) > 1 else ''}. "
             f"{'Wait, you do that too, right?' if a_top in shared else 'Have you ever tried it?'}",
        f"Sharing {A}'s real routine. {'This is a shared thing, leaning in.' if a_top in shared else 'Testing if ' + B + ' is open to it.'}")

    if a_top in shared:
        say(idb, r.choice(["Yes! Okay this changes things. We have to do that together sometime.",
                           "No way. Okay, now I want to know your favourite spot for it."]),
            f"Real overlap on {a_top.lower()}. Chemistry going up.")
    elif "adventurous" in b.personality or "curious" in b.personality:
        say(idb, "Never, but I'd try it. I'm usually up for anything once.", f"Not my thing yet, but I'm open. {A} might widen my world.")
    else:
        say(idb, "Not really my thing, if I'm being honest. But I like that you have something you're that into.",
            f"No overlap here. Respect the passion, but noting it.")

    a_need = a.needs[0] if a.needs else "someone kind"
    say(ida, f"Can I ask a slightly bigger question? What do you actually need from someone? Not the dating-app answer.",
        f"Probing needs. {A} needs: {a_need.lower()}.")
    b_need = b.needs[0] if b.needs else "someone kind and consistent"
    say(idb, f"Hm. Honestly? {b_need}. I've learned that the hard way.",
        f"Told the truth. Watching how {A} reacts.")

    if c.dealbreakers_a:
        db = c.dealbreakers_a[0]
        say(ida, f"I appreciate that. I'll be honest too, something that doesn't work for me is {db.lower()}. How do you feel about that?",
            f"Red flag check: {B}'s traits brush up against {A}'s dealbreaker ({db.lower()}).")
        say(idb, r.choice(["That's fair. I'd be lying if I said that's never me.", "Hm, okay. I think I'm a bit like that, yeah."]),
            "Honest friction. Not hiding it.")
    else:
        fit = len(c.shared_values) > 0 or c.energy_match
        say(ida, (f"That actually makes a lot of sense to me. I think I'd be good at that." if fit
                  else f"I get that. I'm not sure I'm naturally that person, but I respect knowing what you want."),
            f"{'Their need fits what ' + A + ' can give.' if fit else 'Need mismatch, logging it.'}")
        say(idb, (f"And yours? You've got a {', '.join(a.personality[:2])} vibe, so I'm guessing it's something like {a_need.lower()}?"
                  ), f"Testing whether I read {A} right.")

    good = c.prior >= 5
    say(ida, r.choice(["This was genuinely fun. I'd like to do it again." if good else "This was really nice, thank you for coming.",
                       f"Next time I'm picking {VENUES.get(shared[0], 'somewhere new') if shared else 'somewhere new'}, if you're up for it." if good else
                       "I'm glad we did this. Get home safe."]),
        f"Closing. Gut read: {'second date' if good else 'probably friends'}.")
    say(idb, ("I'd really like that. Text me." if good else "Same, it was lovely meeting you."),
        f"{'Would see ' + A + ' again.' if good else 'Nice, but not the one.'}")
    return T


def _verdict_offline(me: Analysis, other: Analysis, pid: str, c: Compat, mine_db: list[str], theirs_db: list[str]) -> Verdict:
    r = random.Random(hash((pid, other.display_name)) & 0xffffffff)
    shared = c.shared_hobbies + c.shared_interests
    chem = min(9.6, 2.6 + 1.4 * len(c.shared_hobbies) + 0.6 * len(c.shared_interests) + (1 if c.energy_match else -1) + r.uniform(-0.6, 0.6))
    needs_met = min(9.5, 3.4 + 1.3 * len(c.shared_values) + (1.5 if c.energy_match else 0) - 2.5 * len(mine_db) + r.uniform(-0.5, 0.5))
    vals = min(9.5, 3.0 + 1.7 * len(c.shared_values) + 0.4 * len(c.shared_interests))
    score = max(0.0, min(10.0, 0.4 * chem + 0.4 * needs_met + 0.2 * vals - (1.5 if mine_db else 0)))
    reasons = []
    if shared:
        reasons.append(f"Real overlap: {', '.join(s.lower() for s in shared[:3])}")
    if c.shared_values:
        reasons.append(f"Shared values: {', '.join(v.lower() for v in c.shared_values[:2])}")
    reasons.append("Social energy matches" if c.energy_match else "Different social energy, would need negotiating")
    if mine_db:
        reasons.append(f"Touched a dealbreaker: {mine_db[0].lower()}")
    if not shared:
        reasons.append("Little shared day-to-day life")
    second = score >= 6.3 and not mine_db
    o = first(other)
    report = (f"{o} and I {'clicked' if score >= 6.5 else 'got on fine' if score >= 4.5 else 'struggled to connect'}"
              f"{' over ' + shared[0].lower() if shared else ''}. "
              f"{'I think they could give you ' + me.needs[0][0].lower() + me.needs[0][1:] + '.' if me.needs and score >= 6.3 else 'I am not convinced they meet what you need.'} "
              f"{'I would say yes to a second date.' if second else 'I would pass, kindly.'}")
    return Verdict(agent_for=pid, score=round(score, 2), chemistry=round(max(0, chem), 2),
                   needs_met=round(max(0, needs_met), 2), values_alignment=round(vals, 2),
                   dealbreaker_hit=bool(mine_db), second_date=second, reasons=reasons, report_to_human=report)


# =================================================================== entry point

def go_on_date(ida: str, a: Analysis, idb: str, b: Analysis) -> DateRecord:
    c = compute(a, b)
    venue, why = pick_venue(a, b, c)
    engine = "offline"
    if config.llm_enabled():
        try:
            turns = _date_llm(a, b, ida, idb, venue)
            va = _verdict_llm(a, b, ida, turns, ida, venue)
            vb = _verdict_llm(b, a, idb, turns, ida, venue)
            engine = "claude"
        except Exception:
            turns = None
    if engine == "offline":
        turns = _date_offline(a, b, ida, idb, venue, c)
        va = _verdict_offline(a, b, ida, c, c.dealbreakers_a, c.dealbreakers_b)
        vb = _verdict_offline(b, a, idb, c, c.dealbreakers_b, c.dealbreakers_a)
    # mutual = harmonic-ish mean so one-sided interest is punished
    mutual = round(2 * va.score * vb.score / (va.score + vb.score), 2) if va.score + vb.score else 0.0
    did = hashlib.sha1(f"{ida}|{idb}".encode()).hexdigest()[:10]
    return DateRecord(id=did, a=ida, b=idb, venue=venue, venue_reason=why, turns=turns,
                      verdict_a=va, verdict_b=vb, mutual=mutual, engine=engine)
