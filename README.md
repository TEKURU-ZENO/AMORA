# AgentDate

**In one breath (185 chars):** Paste a LinkedIn and a public Instagram. An agent reads both, writes an evidence-backed profile, then goes on real turn-by-turn dates with every other agent and ranks who fits you best.

## How it works

```
LinkedIn (public) + Instagram (public)      <- the only two sources, plus the person's consent
        |  Apify actors
        v
Analyst agent: 3 passes (LinkedIn, Instagram, cross-read)
        v
Profile page: needs, hobbies, interests, values, personality, lifestyle,
              dealbreakers, ideal date, reading log, evidence snippet per claim
        v
Screening: each agent sees everyone's public card, asks out its top K
        v
Dates: inviter picks a venue from shared interests; two agents talk in turns,
       each holding a private brief of its human + a private thought per turn
        v
Verdicts: each agent reports to its own human (chemistry, needs met, values,
          dealbreaker hit, second date y/n)
        v
Rankings: fit(X,Y) = 0.6 * X's agent score + 0.4 * Y's agent score - dealbreaker penalty
```

Design decisions worth knowing:

- **Agents act for one person only.** Each dating agent sees its own human's full analysis but only the other person's public card. It never sees the other side's private brief or verdict, so it has to find things out on the date.
- **Every turn has two channels.** `say` is what the date hears, `thought` is the agent's running read for its human. The replay page can toggle thoughts on, which is the best part of the demo.
- **Verdicts are independent and asymmetric.** A can love B while B passes. The mutual score uses a harmonic mean so one-sided interest is punished, and rankings weight your own agent's opinion higher.
- **Analysis is evidence-first.** Each claim on the profile links to a snippet from LinkedIn or Instagram. The analyst is told never to infer protected attributes or comment on looks.
- **Two engines.** With `ANTHROPIC_API_KEY` set, all agents run on Claude (structured outputs via forced tool use). Without it, a deterministic offline engine (keyword taxonomy + compatibility model) runs the same pipeline, so the site and tests never break.

## Technical section: scraping

| Source | Tool | Notes |
|---|---|---|
| Instagram | Apify `apify/instagram-profile-scraper` via the `run-sync-get-dataset-items` REST endpoint (`httpx`) | Pulls bio, counts and up to 24 recent posts (caption, hashtags, location, type). Private profiles are rejected. |
| LinkedIn | Apify LinkedIn public-profile actor (default `dev_fusion/linkedin-profile-scraper`, set `APIFY_LINKEDIN_ACTOR` to swap) | Pulls headline, about, location, experience, education, skills, volunteering, languages. |

Actor output is normalized into our own Pydantic models (`app/scrape/apify.py`), so swapping actors only touches two functions. Links are validated first: LinkedIn must be `/in/<handle>`, Instagram must be a profile, not a post.

Rest of the stack: FastAPI, Jinja templates, server-sent events for live progress, SQLite, Anthropic SDK, Pydantic v2.

## Consent

People get into the pool by pasting **their own** links on `/join` (or someone does it with their permission) and ticking consent. Anyone can remove themselves from their profile page, which deletes their data and dates. The bulk seeder only accepts CSV rows marked `consent=yes`. We don't discover or scrape people who haven't opted in.

## Run it

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...   # optional, enables Claude agents
export APIFY_TOKEN=...         # required for pasting real links
python -m scripts.seed --csv optins.csv      # real opted-in people, then a dating round
# or: python -m scripts.seed --synthetic     # 25 fictional test personas, no network
uvicorn app.main:app --reload
pytest -q
```

Deploy: `render.yaml` (Render) or the `Dockerfile` (any container host). Mount a disk at `DATA_DIR` so the SQLite file survives restarts.

| Env var | Default | |
|---|---|---|
| `AGENTDATE_MODEL` | `claude-sonnet-4-5` | model for all agents |
| `SHORTLIST_K` | 6 | how many people each agent asks out |
| `DATE_TURNS` | 10 | messages per date |
| `MAX_PARALLEL_DATES` | 6 | concurrent dates with Claude |

## Pages

`/` pool, paste links, run a round · `/join` opt-in · `/person/<id>` live reading screen while the analyst works, then the profile with receipts, best fits, dates · `/round` the dating floor: ask-out arcs and a live wall of dates · `/date/<id>` animated replay with private thoughts and verdict reveal · `/dates` all dates · `/rankings` top 5 per person, highlights and an everyone × everyone matrix · `/how` · `/api/export` JSON snapshot
