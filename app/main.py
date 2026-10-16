from __future__ import annotations

import asyncio
import functools
import json
import threading
import uuid

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import config, discovery, harness, privacy, store
from .config import ROOT



app = FastAPI(title="AMORA")
app.mount("/static", StaticFiles(directory=ROOT / "app" / "static"), name="static")
tpl = Jinja2Templates(directory=ROOT / "app" / "templates")
# a stable monogram tint per person (app.js uses the same formula)
tpl.env.filters["tint"] = lambda pid: f"t{sum(map(ord, pid)) % 7}"
store.init()


def _autoseed_demo() -> None:
    """Demo mode with an empty pool: add the fictional personas and run one round, so the site is
    populated at once. Serverless hosts (Vercel) start with an empty /tmp and may stop background
    jobs, so this runs inline at startup rather than as a job."""
    if config.demo_mode() and not any(p.analysis for p in store.list_persons()):
        harness.add_demo_personas(progress=lambda m: None)
        harness.run_round(progress=lambda m: None)


_autoseed_demo()

JOBS: dict[str, dict] = {}
PERSON_JOBS: dict[str, str] = {}  # person id -> ingest job, so their page can show the live reading
ROUND = {"job": None}  # the dating round currently running, if any


def _job(fn, *args, job_type: str = "task", idempotency_key: str | None = None, entity_id: str | None = None) -> str:
    jid = uuid.uuid4().hex[:10]
    job_record, is_new = store.create_or_get_job(jid, job_type, idempotency_key=idempotency_key, entity_id=entity_id)
    if not is_new:
        return job_record["id"]

    jid = job_record["id"]
    JOBS[jid] = {"log": list(store.get_job_logs(jid)), "done": False, "error": None, "result": None}
    store.update_job(jid, status="running")

    def progress(msg):  # a plain string for the log, or a dict event for the live screens
        JOBS[jid]["log"].append(msg)
        store.append_job_log(jid, msg)

    def run():
        try:
            res = fn(*args, progress=progress)
            JOBS[jid]["result"] = res
            store.update_job(jid, status="succeeded", stage="completed")
        except Exception as e:
            JOBS[jid]["error"] = str(e)
            store.update_job(jid, status="failed", error=str(e))
            progress(f"error: {e}")
        finally:
            JOBS[jid]["done"] = True

    threading.Thread(target=run, daemon=True).start()
    return jid


def _running(jid) -> bool:
    if not jid:
        return False
    if jid in JOBS:
        return not JOBS[jid]["done"]
    job = store.get_job(jid)
    return bool(job and job["status"] in ("queued", "running"))



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
            "llm": config.llm_enabled(), "scraping": config.scraping_enabled(), "demo": config.demo_mode(), **kw}


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
def join(request: Request, token: str = ""):
    cand = discovery.registry.get_candidate_by_token(token) if token else None
    return tpl.TemplateResponse(request, "join.html", _ctx(request, candidate=cand))



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
    authorized = privacy.is_authorized(request)
    sanitized_d = privacy.sanitize_date(d, authorized=authorized)
    return tpl.TemplateResponse(request, "date.html", _ctx(request, d=sanitized_d, authorized=authorized))



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


@app.get("/discovery", response_class=HTMLResponse)
def discovery_page(request: Request):
    candidates = discovery.registry.list_candidates()
    job = request.query_params.get("job")
    return tpl.TemplateResponse(request, "discovery.html", _ctx(
        request, candidates=candidates, job=job if _running(job) else None))


@app.post("/api/discovery/search")
def discovery_search(query: str = Form(""), limit: int = Form(6)):
    if not (config.scraping_enabled() or config.demo_mode()):
        return JSONResponse({"error": "Discovery searches the web through Apify, and no APIFY_TOKEN is set on this server."}, 503)
    # Real searches and Instagram scrapes take minutes, so this runs as a job the page streams.
    jid = _job(discovery.orchestrator.run_discovery_batch, query, max(1, min(limit, 20)), job_type="discovery")
    return RedirectResponse(f"/discovery?job={jid}", status_code=303)


@app.post("/api/discovery/candidates/{cid}/review")
def discovery_review(cid: str, action: str = Form(...)):
    cand = discovery.registry.get_candidate(cid)
    if not cand:
        raise HTTPException(404, "Candidate not found")
    if action == "approve":
        token = cand.invitation_token or f"inv_{uuid.uuid4().hex[:16]}"
        cand.status = "verified_crosslink"
        cand.verification_method = "human_review"
        cand.verification_evidence = "Verified and approved by human reviewer"
        cand.invitation_token = token
        cand.rejection_reason = None
        discovery.registry.save_candidate(cand)
    elif action == "reject":
        cand.status = "rejected"
        cand.rejection_reason = "Rejected upon human review"
        discovery.registry.save_candidate(cand)
    return RedirectResponse("/discovery", status_code=303)


# ---------------------------------------------------------------- actions

@app.post("/api/people")
def add_person(linkedin: str = Form(...), instagram: str = Form(...), consent: str = Form(""), token: str = Form("")):
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
    if token:
        cand = discovery.registry.get_candidate_by_token(token)
        if cand:
            discovery.registry.update_status(cand.id, "consented", evidence="Participant consented via invitation")
    pid = person_id(normalize_linkedin(linkedin)[1], normalize_instagram(instagram)[1])
    if not _reading(pid):
        PERSON_JOBS[pid] = _job(harness.ingest, linkedin, instagram, True, job_type="ingest", idempotency_key=f"ingest:{pid}", entity_id=pid)
    return {"job": PERSON_JOBS[pid], "person": pid}



@app.post("/api/round")
def start_round():
    if not _round_running():  # one round at a time; a second click joins the running one
        ROUND["job"] = _job(harness.run_round, job_type="round", idempotency_key="round:active")
    return {"job": ROUND["job"]}


@app.post("/api/people/{pid}/date")
def date_the_pool(pid: str):
    """This person's agent asks out the existing pool (demo personas included) and goes on the dates."""
    p = store.get_person(pid)
    if not p or not p.analysis:
        return JSONResponse({"error": "That profile isn't ready to date yet."}, 404)
    if len([x for x in store.list_persons() if x.analysis]) < 2:
        return JSONResponse({"error": "A round needs at least two people in the pool."}, 400)
    if not _round_running():  # shares the round slot, so two runs never write dates at once
        ROUND["job"] = _job(functools.partial(harness.run_round, only=pid), job_type="round",
                            idempotency_key="round:active")
    return {"job": ROUND["job"]}


@app.post("/api/demo/personas")
def add_demo_personas():
    if not config.demo_mode():
        return JSONResponse({"error": "Demo personas are only available in demo mode (AMORA_DEMO=1)."}, 403)
    return {"job": _job(harness.add_demo_personas, job_type="demo_seed", idempotency_key="demo:personas")}


@app.get("/api/jobs/{jid}/stream")
async def stream(jid: str):
    persisted_job = store.get_job(jid)
    if jid not in JOBS and not persisted_job:
        raise HTTPException(404)

    async def gen():
        sent = 0
        while True:
            logs = JOBS[jid]["log"] if jid in JOBS else store.get_job_logs(jid)
            while sent < len(logs):
                item = logs[sent]
                yield f"data: {json.dumps({'event': item} if isinstance(item, dict) else {'msg': item})}\n\n"
                sent += 1
            is_done = JOBS[jid]["done"] if jid in JOBS else (persisted_job and persisted_job["status"] in ("succeeded", "failed", "cancelled"))
            if is_done:
                err = JOBS[jid]["error"] if jid in JOBS else (persisted_job.get("error") if persisted_job else None)
                res = JOBS[jid].get("result") if jid in JOBS else None
                extra = {"person": res.id} if hasattr(res, "id") else ({"person": persisted_job.get("entity_id")} if persisted_job and persisted_job.get("entity_id") else {})
                yield f"data: {json.dumps({'done': True, 'error': err, **extra})}\n\n"
                return
            await asyncio.sleep(0.3)

    return StreamingResponse(gen(), media_type="text/event-stream")



@app.post("/person/{pid}/delete")
def delete(pid: str):
    if pid in PERSON_JOBS:
        jid = PERSON_JOBS[pid]
        if jid in JOBS:
            JOBS[jid]["done"] = True
            JOBS[jid]["error"] = "Job cancelled: person deleted"
    store.delete_person(pid)
    try:
        store.set_meta("rankings", harness.compute_rankings())
    except Exception:
        pass
    return RedirectResponse("/", status_code=303)


@app.post("/person/{pid}/revoke-consent")
def revoke_consent(pid: str):
    p = store.get_person(pid)
    if not p:
        raise HTTPException(404, "No such person")
    if pid in PERSON_JOBS:
        jid = PERSON_JOBS[pid]
        if jid in JOBS:
            JOBS[jid]["done"] = True
            JOBS[jid]["error"] = "Job cancelled: consent revoked"
    store.revoke_consent(pid)
    try:
        store.set_meta("rankings", harness.compute_rankings())
    except Exception:
        pass
    return JSONResponse({
        "status": "revoked",
        "person": pid,
        "message": "Consent successfully revoked. Participant will not be paired or dated."
    })


@app.get("/api/export")
def export():
    """Sanitized public export: inner agent thoughts and raw scraping data are stripped."""
    return {
        "people": [privacy.sanitize_person_dict(p, authorized=False) for p in store.list_persons()],
        "dates": [privacy.sanitize_date_dict(d, authorized=False) for d in store.list_dates()],
        "rankings": store.get_meta("rankings", {})
    }


@app.get("/api/admin/export")
def admin_export(request: Request):
    """Authorized administrative export: contains full date replays including agent thoughts."""
    privacy.require_auth(request)
    return {
        "people": [privacy.sanitize_person_dict(p, authorized=True) for p in store.list_persons()],
        "dates": [privacy.sanitize_date_dict(d, authorized=True) for d in store.list_dates()],
        "rankings": store.get_meta("rankings", {})
    }



@app.get("/healthz")
def health():
    import os
    # which deploy is answering (Vercel sets these): tells a missing env var apart from a stale deploy
    return {"ok": True, "llm": config.llm_enabled(), "scraping": config.scraping_enabled(), "demo": config.demo_mode(),
            "demo_var_set": bool(os.getenv("AMORA_DEMO") or os.getenv("AGENTDATE_DEMO")),
            "env": os.getenv("VERCEL_ENV", "local"), "commit": os.getenv("VERCEL_GIT_COMMIT_SHA", "")[:7]}
