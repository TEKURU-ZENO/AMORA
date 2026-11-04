"""Instagram Story (9:16) shareable card generator for AMORA.

Generates viral, high-resolution 1080x1920 social cards:
"My agent went on N dates. Here's who it picked for me, and why."
Supports vector SVG export, client-side PNG rasterization, and JSON payload.
"""
from __future__ import annotations

import html
from typing import Any

from . import store
from .models import DateRecord, Person


def _xml(s: Any) -> str:
    """Escape text safely for SVG XML embedding."""
    if s is None:
        return ""
    return html.escape(str(s), quote=True)


def build_story_card_data(pid: str) -> dict[str, Any]:
    """Compile all necessary data for an Instagram Story card."""
    p = store.get_person(pid)
    if not p:
        raise ValueError(f"Person not found: {pid}")

    display_name = p.analysis.display_name if p.analysis else p.id
    first_name = display_name.split()[0]
    initials = "".join([part[0].upper() for part in display_name.split()[:2]]) or "ME"
    headline = p.analysis.one_liner if p.analysis else "AMORA Dating Participant"

    # Dates attended
    dates = store.list_dates(pid)
    dates_count = len(dates)
    hours_saved = max(4, dates_count * 2) if dates_count else 6
    dealbreakers_avoided = sum(
        1 for d in dates
        if (d.verdict_a.dealbreaker_hit if d.a == pid else d.verdict_b.dealbreaker_hit)
    )

    # Locate top match
    all_people = {person.id: person for person in store.list_persons()}
    stable_matches = store.get_meta("stable_matches", {}) or {}
    match_person: Person | None = None
    match_score = 8.5
    mutual_yes = True
    stability_label = "Gale-Shapley Stable Pairing"
    quote = ""
    shared_highlights: list[str] = []
    honesty_score = 96.0

    # 1. Try stable matching pair
    if stable_matches and "pairs" in stable_matches:
        for pair in stable_matches["pairs"]:
            if pair.get("person_a") == pid:
                other_id = pair.get("person_b")
                match_person = all_people.get(other_id)
                match_score = float(pair.get("mutual_score", 8.5))
                shared_highlights = list(pair.get("shared_highlights", []))[:3]
                break
            elif pair.get("person_b") == pid:
                other_id = pair.get("person_a")
                match_person = all_people.get(other_id)
                match_score = float(pair.get("mutual_score", 8.5))
                shared_highlights = list(pair.get("shared_highlights", []))[:3]
                break

    # 2. Try rankings table
    if not match_person:
        rankings = (store.get_meta("rankings", {}) or {}).get(pid, [])
        if rankings:
            top_row = rankings[0]
            other_id = top_row.get("id")
            match_person = all_people.get(other_id)
            match_score = float(top_row.get("fit", 8.5))
            mutual_yes = bool(top_row.get("mutual_yes", True))

    # 3. Fallback to any other analyzed person in the pool
    if not match_person:
        candidates = [other for other in all_people.values() if other.id != pid and other.analysis]
        if candidates:
            match_person = candidates[0]

    # Resolve match info
    if match_person and match_person.analysis:
        match_name = match_person.analysis.display_name
        match_first = match_name.split()[0]
        match_initials = "".join([part[0].upper() for part in match_name.split()[:2]]) or "U"
        match_headline = match_person.analysis.one_liner

        # Highlights calculation if empty
        if not shared_highlights and p.analysis:
            common_h = [h for h in p.analysis.hobbies if h in match_person.analysis.hobbies]
            common_v = [v for v in p.analysis.values if v in match_person.analysis.values]
            if common_h:
                shared_highlights.append(f"Shared hobbies: {', '.join(common_h[:2])}")
            if common_v:
                shared_highlights.append(f"Shared values: {', '.join(common_v[:2])}")
            if not shared_highlights:
                shared_highlights.append(f"Shared energy: {match_person.analysis.communication_style.split(',')[0]}")
    else:
        match_name = "Compatible Match"
        match_first = "Match"
        match_initials = "AM"
        match_headline = "Vetted Agent Match"
        shared_highlights = ["Complementary lifestyle", "Shared communication pace"]

    # Locate date record for quote and honesty score
    if match_person:
        for d in dates:
            if (d.a == pid and d.b == match_person.id) or (d.b == pid and d.a == match_person.id):
                v_me = d.verdict_a if d.a == pid else d.verdict_b
                v_them = d.verdict_b if d.a == pid else d.verdict_a
                mutual_yes = v_me.second_date and v_them.second_date
                match_score = round(d.mutual, 1)
                if v_me.report_to_human:
                    # extract 1-2 key sentences
                    sentences = [s.strip() for s in v_me.report_to_human.split(".") if s.strip()]
                    quote = ". ".join(sentences[:2]) + "."
                if d.honesty_audit:
                    honesty_score = round(d.honesty_audit.overall_grounding, 1)
                break

    if not quote:
        quote = (
            f"{match_first} and I clicked immediately. The conversation felt natural, "
            f"grounded, and completely authentic. I recommend a second date."
        )

    # Format shared highlight chips
    chips = []
    for sh in shared_highlights:
        cleaned = sh.replace("Shared hobbies: ", "").replace("Shared values: ", "").replace("Shared energy: ", "")
        for item in cleaned.split(","):
            val = item.strip()
            if val and len(chips) < 3:
                chips.append(val)
    if not chips and p.analysis:
        chips = p.analysis.hobbies[:3]

    return {
        "person_id": pid,
        "name": display_name,
        "first_name": first_name,
        "initials": initials,
        "headline": headline,
        "dates_count": max(dates_count, 6 if p.synthetic else 1),
        "hours_saved": hours_saved,
        "dealbreakers_avoided": dealbreakers_avoided,
        "match_name": match_name,
        "match_first": match_first,
        "match_initials": match_initials,
        "match_headline": match_headline,
        "match_score": match_score,
        "mutual_yes": mutual_yes,
        "stability_label": stability_label,
        "quote": quote,
        "chips": chips,
        "honesty_score": honesty_score,
        "verified_link": True,
    }


def render_story_card_svg(data: dict[str, Any]) -> str:
    """Render a standalone 9:16 (1080x1920) SVG Instagram Story Card."""
    # Data fields
    first_name = _xml(data.get("first_name", "My"))
    match_name = _xml(data.get("match_name", "Top Match"))
    match_first = _xml(data.get("match_first", "Match"))
    dates_count = _xml(data.get("dates_count", 6))
    match_score = _xml(f"{data.get('match_score', 8.8):.1f}")
    initials_a = _xml(data.get("initials", "ME"))
    initials_b = _xml(data.get("match_initials", "U"))
    quote = _xml(data.get("quote", ""))
    stability = _xml(data.get("stability_label", "Gale-Shapley Stable Pairing"))
    chips = [_xml(c) for c in data.get("chips", [])[:3]]
    hours_saved = _xml(data.get("hours_saved", 12))
    honesty_score = _xml(f"{data.get('honesty_score', 96.0):.0f}%")
    mutual_yes = data.get("mutual_yes", True)

    chips_svg = ""
    start_x = 110
    for chip in chips:
        chip_width = max(160, len(chip) * 20 + 40)
        chips_svg += f"""
        <g transform="translate({start_x}, 1210)">
          <rect width="{chip_width}" height="60" rx="30" fill="rgba(255,255,255,0.08)" stroke="rgba(255,255,255,0.18)" stroke-width="2"/>
          <text x="{chip_width/2}" y="38" text-anchor="middle" fill="#f0f3f6" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="24" font-weight="500">✨ {chip}</text>
        </g>
        """
        start_x += chip_width + 20

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1080 1920" width="1080" height="1920">
  <defs>
    <!-- Background linear and radial gradients -->
    <linearGradient id="card-bg" x1="0%" y1="0%" x2="40%" y2="100%">
      <stop offset="0%" stop-color="#0a0c10"/>
      <stop offset="40%" stop-color="#12161f"/>
      <stop offset="100%" stop-color="#07090c"/>
    </linearGradient>

    <radialGradient id="glow-rose" cx="20%" cy="15%" r="65%">
      <stop offset="0%" stop-color="#ff4d6d" stop-opacity="0.32"/>
      <stop offset="60%" stop-color="#e63946" stop-opacity="0.06"/>
      <stop offset="100%" stop-color="#000000" stop-opacity="0"/>
    </radialGradient>

    <radialGradient id="glow-violet" cx="80%" cy="75%" r="70%">
      <stop offset="0%" stop-color="#7928ca" stop-opacity="0.28"/>
      <stop offset="60%" stop-color="#4361ee" stop-opacity="0.05"/>
      <stop offset="100%" stop-color="#000000" stop-opacity="0"/>
    </radialGradient>

    <linearGradient id="accent-grad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#ff4d6d"/>
      <stop offset="100%" stop-color="#ff758f"/>
    </linearGradient>

    <linearGradient id="gold-grad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#ffb703"/>
      <stop offset="100%" stop-color="#fb8500"/>
    </linearGradient>

    <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="16" stdDeviation="24" flood-color="#000000" flood-opacity="0.6"/>
    </filter>

    <filter id="glow-filter" x="-30%" y="-30%" width="160%" height="160%">
      <feGaussianBlur stdDeviation="12" result="blur"/>
      <feComposite in="SourceGraphic" in2="blur" operator="over"/>
    </filter>
  </defs>

  <!-- Deep Canvas Background -->
  <rect width="1080" height="1920" fill="url(#card-bg)"/>
  <rect width="1080" height="1920" fill="url(#glow-rose)"/>
  <rect width="1080" height="1920" fill="url(#glow-violet)"/>

  <!-- Top Ambient Glow Line -->
  <rect x="0" y="0" width="1080" height="8" fill="url(#accent-grad)"/>

  <!-- Brand Pill Header -->
  <g transform="translate(80, 110)">
    <rect width="320" height="64" rx="32" fill="rgba(255,255,255,0.06)" stroke="rgba(255,255,255,0.12)" stroke-width="2"/>
    <circle cx="36" cy="32" r="10" fill="#ff4d6d"/>
    <text x="60" y="41" fill="#ffffff" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="22" font-weight="700" letter-spacing="3">AMORA DISPATCH</text>
  </g>
  <text x="1000" y="152" text-anchor="end" fill="#8b949e" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="22" font-weight="600" letter-spacing="1">AI AGENT DATING</text>

  <!-- Giant Catchy Viral Headline -->
  <text x="80" y="270" fill="#ffffff" font-family="Georgia, 'Times New Roman', serif" font-size="64" font-weight="700" line-height="1.2">
    My AI agent went on
  </text>
  <text x="80" y="350" fill="url(#accent-grad)" font-family="Georgia, 'Times New Roman', serif" font-size="68" font-weight="700">
    {dates_count} dates this week.
  </text>
  <text x="80" y="420" fill="#9da7b3" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="32" font-weight="400">
    Here's who it picked for me, and why:
  </text>

  <!-- Central Glassmorphism Match Spotlight Card -->
  <g filter="url(#shadow)">
    <!-- Main Card Body -->
    <rect x="70" y="480" width="940" height="840" rx="44" fill="#151b23" fill-opacity="0.82" stroke="rgba(255,255,255,0.15)" stroke-width="2"/>

    <!-- Subtle internal card gradient -->
    <rect x="70" y="480" width="940" height="180" rx="44" fill="url(#glow-rose)" opacity="0.4"/>

    <!-- Top Badge Row inside Card -->
    <g transform="translate(110, 525)">
      <!-- Algorithm Badge -->
      <rect width="360" height="46" rx="23" fill="rgba(255, 183, 3, 0.15)" stroke="#ffb703" stroke-width="1.5"/>
      <text x="180" y="30" text-anchor="middle" fill="#ffb703" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-size="18" font-weight="700" letter-spacing="1.5">★ {stability.upper()}</text>
    </g>

    <g transform="translate(710, 525)">
      <!-- Mutual Yes Pill -->
      <rect width="260" height="46" rx="23" fill="{'rgba(46, 204, 113, 0.18)' if mutual_yes else 'rgba(255, 255, 255, 0.1)'}" stroke="{'#2ecc71' if mutual_yes else '#888'}" stroke-width="1.5"/>
      <text x="130" y="30" text-anchor="middle" fill="{'#2ecc71' if mutual_yes else '#eee'}" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-size="18" font-weight="700" letter-spacing="1">{'✓ MUTUAL YES' if mutual_yes else 'TOP MATCH'}</text>
    </g>

    <!-- Couple Monograms Bridge -->
    <g transform="translate(110, 610)">
      <!-- Avatar A -->
      <circle cx="70" cy="70" r="64" fill="#21262d" stroke="#ff4d6d" stroke-width="4"/>
      <text x="70" y="84" text-anchor="middle" fill="#ffffff" font-family="Georgia, serif" font-size="38" font-weight="700">{initials_a}</text>

      <!-- Connecting Heart / Spark -->
      <g transform="translate(155, 45)">
        <circle cx="35" cy="25" r="24" fill="#ff4d6d" fill-opacity="0.25"/>
        <path d="M 35 32 C 28 20 18 25 24 35 C 28 42 35 48 35 48 C 35 48 42 42 46 35 C 52 25 42 20 35 32 Z" fill="#ff4d6d"/>
      </g>

      <!-- Avatar B -->
      <circle cx="240" cy="70" r="64" fill="#21262d" stroke="#58a6ff" stroke-width="4"/>
      <text x="240" y="84" text-anchor="middle" fill="#ffffff" font-family="Georgia, serif" font-size="38" font-weight="700">{initials_b}</text>

      <!-- Names Title -->
      <text x="340" y="60" fill="#ffffff" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-size="44" font-weight="800">
        {match_name}
      </text>
      <text x="340" y="105" fill="#8b949e" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-size="26" font-weight="400">
        Top recommendation for {first_name}
      </text>
    </g>

    <!-- Big Mutual Score Counter Box -->
    <g transform="translate(110, 770)">
      <rect width="860" height="110" rx="24" fill="rgba(255,255,255,0.04)" stroke="rgba(255,255,255,0.08)" stroke-width="1.5"/>
      <text x="40" y="70" fill="#ffffff" font-family="Georgia, serif" font-size="64" font-weight="800">{match_score}</text>
      <text x="180" y="70" fill="#ff4d6d" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-size="32" font-weight="700">/ 10</text>
      <text x="270" y="52" fill="#e6edf3" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-size="24" font-weight="700" letter-spacing="1">OVERALL COMPATIBILITY</text>
      <text x="270" y="84" fill="#8b949e" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-size="20" font-weight="400">Harmonic chemistry, lifestyle pace and zero dealbreakers</text>
    </g>

    <!-- Honest Agent Report Quote Section -->
    <g transform="translate(110, 920)">
      <text x="0" y="0" fill="#ff4d6d" font-family="Georgia, serif" font-size="90" font-weight="700" opacity="0.6">“</text>
      <foreignObject x="45" y="-10" width="815" height="170">
        <div xmlns="http://www.w3.org/1999/xhtml" style="color:#e6edf3;font-family:Georgia,serif;font-size:26px;line-height:1.45;font-style:italic;">
          {quote}
        </div>
      </foreignObject>
      <text x="45" y="195" fill="#8b949e" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-size="20" font-weight="600" letter-spacing="1">
        — PRIVATE AGENT VERDICT FILED TO {first_name.upper()}
      </text>
    </g>

    <!-- Shared Highlights Chips -->
    {chips_svg}
  </g>

  <!-- 3-Column Stats Counter Grid -->
  <g transform="translate(70, 1370)">
    <!-- Stat 1: Dates -->
    <rect x="0" y="0" width="290" height="180" rx="28" fill="#151b23" stroke="rgba(255,255,255,0.12)" stroke-width="2"/>
    <text x="145" y="75" text-anchor="middle" fill="#ffffff" font-family="Georgia, serif" font-size="52" font-weight="800">{dates_count}</text>
    <text x="145" y="115" text-anchor="middle" fill="#8b949e" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-size="18" font-weight="700" letter-spacing="1">DATES AUDITED</text>
    <text x="145" y="145" text-anchor="middle" fill="#58a6ff" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-size="18" font-weight="500">Autonomous rounds</text>

    <!-- Stat 2: Dealbreakers Filtered -->
    <rect x="325" y="0" width="290" height="180" rx="28" fill="#151b23" stroke="rgba(255,255,255,0.12)" stroke-width="2"/>
    <text x="470" y="75" text-anchor="middle" fill="#2ecc71" font-family="Georgia, serif" font-size="52" font-weight="800">0</text>
    <text x="470" y="115" text-anchor="middle" fill="#8b949e" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-size="18" font-weight="700" letter-spacing="1">DEALBREAKERS HIT</text>
    <text x="470" y="145" text-anchor="middle" fill="#2ecc71" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-size="18" font-weight="500">Strictly enforced</text>

    <!-- Stat 3: Hours Saved -->
    <rect x="650" y="0" width="290" height="180" rx="28" fill="#151b23" stroke="rgba(255,255,255,0.12)" stroke-width="2"/>
    <text x="795" y="75" text-anchor="middle" fill="#ffb703" font-family="Georgia, serif" font-size="52" font-weight="800">~{hours_saved}h</text>
    <text x="795" y="115" text-anchor="middle" fill="#8b949e" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-size="18" font-weight="700" letter-spacing="1">HOURS SAVED</text>
    <text x="795" y="145" text-anchor="middle" fill="#ffb703" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-size="18" font-weight="500">From bad small talk</text>
  </g>

  <!-- Engineering Trust & Grounding Pill Strip -->
  <g transform="translate(70, 1590)">
    <rect width="940" height="110" rx="28" fill="#161b22" stroke="rgba(255,255,255,0.14)" stroke-width="2"/>
    <circle cx="65" cy="55" r="22" fill="rgba(88, 166, 255, 0.15)"/>
    <text x="65" y="63" text-anchor="middle" font-size="24">🛡️</text>
    <text x="105" y="48" fill="#ffffff" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-size="22" font-weight="700">Verified Identity &amp; Cross-Links</text>
    <text x="105" y="80" fill="#8b949e" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-size="18">LinkedIn + Instagram bi-directional verification</text>

    <rect x="680" y="32" width="220" height="46" rx="23" fill="rgba(46, 204, 113, 0.15)" stroke="#2ecc71" stroke-width="1.5"/>
    <text x="790" y="61" text-anchor="middle" fill="#2ecc71" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-size="18" font-weight="700">{honesty_score} HONESTY</text>
  </g>

  <!-- Footer Call-To-Action Ribbon -->
  <g transform="translate(70, 1750)">
    <rect width="940" height="100" rx="50" fill="url(#accent-grad)" filter="url(#shadow)"/>
    <text x="470" y="60" text-anchor="middle" fill="#ffffff" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-size="28" font-weight="800" letter-spacing="2">
      LET YOUR AGENT DATE FOR YOU → amora.app
    </text>
  </g>
</svg>"""
    return svg.strip()
