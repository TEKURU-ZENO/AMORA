from __future__ import annotations

import asyncio
import json
import threading
import uuid

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import config, harness, store
from .config import ROOT

app = FastAPI(title="AgentDate")
app.mount("/static", StaticFiles(directory=ROOT / "app" / "static"), name="static")
tpl = Jinja2Templates(directory=ROOT / "app" / "templates")
# a stable monogram tint per person (app.js uses the same formula)
tpl.env.filters["tint"] = lambda pid: f"t{sum(map(ord, pid)) % 7}"
store.init()

JOBS: dict[str, dict] = {}
PERSON_JOBS: dict[str, str] = {}  # person id -> ingest job, so their page can show the live reading
ROUND = {"job": None}  # the dating round currently running, if any


def _job(fn, *args) -> str:
    jid = uuid.uuid4().hex[:10]
    JOBS[jid] = {"log": [], "done": False, "error": None, "result": None}

    def progress(msg):  # a plain string for the log, or a dict event for the live screens
        JOBS[jid]["log"].append(msg)

    def run():
        try:
            JOBS[jid]["result"] = fn(*args, progress=progress)
        except Exception as e:
            JOBS[jid]["error"] = str(e)
            progress(f"error: {e}")
        finally:
            JOBS[jid]["done"] = True

    threading.Thread(target=run, daemon=True).start()
    return jid


def _running(jid) -> bool:
    return bool(jid) and jid in JOBS and not JOBS[jid]["done"]


def _round_running() -> bool:
    return _running(ROUND["job"])


def _reading(pid: str) -> bool:
    return _running(PERSON_JOBS.get(pid))


def status_of(p) -> str:
    """The one status vocabulary used everywhere: reading / ready / dating / error."""
    if p.status == "error":
        return "error"
    if p.status in ("pending", "scraped") or _reading(p.id):
        return "reading"
    return "dating" if _round_running() else "ready"


def first_name(p) -> str:
    return (p.analysis.display_name if p.analysis else p.id).split()[0]


def _ctx(request, **kw):
    people = store.list_persons()
    return {"request": request, "people": people, "by_id": {p.id: p for p in people},
            "status_of": status_of, "first": first_name, "round_running": _round_running(),
            "llm": config.llm_enabled(), "scraping": config.scraping_enabled(), **kw}


def _highlights(people, dates, asks) -> dict:
    by_id = {p.id: p for p in people}
    dates = [d for d in dates if d.a in by_id and d.b in by_id]
    out = {}
    mutual = [d for d in dates if d.verdict_a.second_date and d.verdict_b.second_date] or dates
    if mutual:
        out["strongest"] = max(mutual, key=lambda d: d.mutual)
    counts: dict[str, int] = {}
    for picks in (asks or {}).values():
        for oid, _ in picks:
            counts[oid] = counts.get(oid, 0) + 1
    counts = {k: v for k, v in counts.items() if k in by_id}
    if counts:
        top = max(counts, key=lambda k: (counts[k], k))
        out["most_asked"] = (by_id[top], counts[top])
    if dates:
        out["one_sided"] = max(dates, key=lambda d: abs(d.verdict_a.score - d.verdict_b.score))
    return out


# ---------------------------------------------------------------- pages

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    ds = store.list_dates()
    rankings = store.get_meta("rankings", {}) or {}
    top = {pid: rows[0] for pid, rows in rankings.items() if rows and rows[0]["dated"]}
    return tpl.TemplateResponse(request, "home.html", _ctx(
        request, n_dates=len(ds), top=top,
        n_mutual=sum(d.verdict_a.second_date and d.verdict_b.second_date for d in ds)))


@app.get("/join", response_class=HTMLResponse)
def join(request: Request):
    return tpl.TemplateResponse(request, "join.html", _ctx(request))


@app.get("/person/{pid}", response_class=HTMLResponse)
def person(request: Request, pid: str):
    p = store.get_person(pid)
    job = PERSON_JOBS.get(pid)
    if _running(job) or (not p and job in JOBS):
        # the analyst is still reading: show the live reading screen instead of a half profile
        return tpl.TemplateResponse(request, "reading.html", _ctx(request, pid=pid, job=job, p=p))
    if not p:
        raise HTTPException(404, "No such person")
    rankings = (store.get_meta("rankings", {}) or {}).get(pid, [])
    evidence = p.analysis.evidence if p.analysis else []

    def receipt(text: str):
        """Index of the evidence item behind a chip, so clicking the chip can show its receipt."""
        t = text.lower()
        for i, e in enumerate(evidence):
            c = e.claim.lower()
            if c == t or t in c or c in t:
                return i
        return None

    return tpl.TemplateResponse(request, "person.html", _ctx(
        request, p=p, dates=store.list_dates(pid), ranking=rankings[:5], receipt=receipt,
        assemble=request.query_params.get("assemble") == "1"))


@app.get("/round", response_class=HTMLResponse)
def round_floor(request: Request):
    people = [p for p in store.list_persons() if p.analysis]
    by_id = {p.id: p for p in people}
    asks = store.get_meta("asks", {}) or {}
    last = {"asks": {k: [{"id": o, "why": w} for o, w in v if o in by_id] for k, v in asks.items() if k in by_id},
            "dates": [harness.date_tile(d, by_id) for d in store.list_dates() if d.a in by_id and d.b in by_id]}
    roster = [{"id": p.id, "name": p.analysis.display_name, "first": first_name(p)} for p in people]
    return tpl.TemplateResponse(request, "round.html", _ctx(
        request, job=ROUND["job"] if _round_running() else None, roster=roster, last=last))


@app.get("/dates", response_class=HTMLResponse)
def dates(request: Request):
    return tpl.TemplateResponse(request, "dates.html", _ctx(request, dates=store.list_dates(), asks=store.get_meta("asks", {})))


@app.get("/date/{did}", response_class=HTMLResponse)
def date(request: Request, did: str):
    d = store.get_date(did)
    if not d:
        raise HTTPException(404, "No such date")
    return tpl.TemplateResponse(request, "date.html", _ctx(request, d=d))


@app.get("/rankings", response_class=HTMLResponse)
def rankings(request: Request):
    rankings = store.get_meta("rankings", {}) or {}
    people = [p for p in store.list_persons() if p.analysis and p.id in rankings]
    matrix = {pid: {r["id"]: r for r in rows} for pid, rows in rankings.items()}
    return tpl.TemplateResponse(request, "rankings.html", _ctx(
        request, rankings=rankings, ranked=people, matrix=matrix,
        hl=_highlights(people, store.list_dates(), store.get_meta("asks", {}))))


@app.get("/how", response_class=HTMLResponse)
def how(request: Request):
    return tpl.TemplateResponse(request, "how.html", _ctx(request))


# ---------------------------------------------------------------- actions

@app.post("/api/people")
def add_person(linkedin: str = Form(...), instagram: str = Form(...), consent: str = Form("")):
    from .scrape.links import LinkError, normalize_instagram, normalize_linkedin, person_id
    try:
        normalize_linkedin(linkedin)
        normalize_instagram(instagram)
    except LinkError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    if consent != "yes":
        return JSONResponse({"error": "Tick the consent box: you must be this person or have their permission."}, 400)
    if not config.scraping_enabled():
        return JSONResponse({"error": "Scraping is off on this server: no APIFY_TOKEN is set, so live links "
                                      "can't be read. Everything else on the site still works."}, 503)
    pid = person_id(normalize_linkedin(linkedin)[1], normalize_instagram(instagram)[1])
    if not _reading(pid):
        PERSON_JOBS[pid] = _job(harness.ingest, linkedin, instagram, True)
    return {"job": PERSON_JOBS[pid], "person": pid}


@app.post("/api/round")
def start_round():
    if not _round_running():  # one round at a time; a second click joins the running one
        ROUND["job"] = _job(harness.run_round)
    return {"job": ROUND["job"]}


@app.get("/api/jobs/{jid}/stream")
async def stream(jid: str):
    if jid not in JOBS:
        raise HTTPException(404)

    async def gen():
        sent = 0
        while True:
            j = JOBS[jid]
            while sent < len(j["log"]):
                item = j["log"][sent]
                yield f"data: {json.dumps({'event': item} if isinstance(item, dict) else {'msg': item})}\n\n"
                sent += 1
            if j["done"]:
                res = j["result"]
                extra = {"person": res.id} if hasattr(res, "id") else {}
                yield f"data: {json.dumps({'done': True, 'error': j['error'], **extra})}\n\n"
                return
            await asyncio.sleep(0.3)

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.post("/person/{pid}/delete")
def delete(pid: str):
    store.delete_person(pid)
    store.set_meta("rankings", harness.compute_rankings())
    return RedirectResponse("/", status_code=303)


@app.get("/api/export")
def export():
    return {"people": [p.model_dump(exclude={"sources"}) for p in store.list_persons()],
            "dates": [d.model_dump() for d in store.list_dates()],
            "rankings": store.get_meta("rankings", {})}


@app.get("/healthz")
def health():
    return {"ok": True, "llm": config.llm_enabled(), "scraping": config.scraping_enabled()}
