#!/usr/bin/env python3
"""HiveWatch control room - local web UI.   Owner: Member 1

Runs only fixed project commands (no user text ever reaches a shell) and listens on
127.0.0.1 only. The terminal demo (scripts/run_demo.sh) keeps working without this UI.

Start:  python3 ui/server.py        then open http://127.0.0.1:8000
"""
import json, os, re, subprocess, sys, threading, time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(os.environ.get("HW_ROOT", Path(__file__).resolve().parent.parent))
OUT = ROOT / "data" / "out"
STATIC = Path(__file__).resolve().parent / "static"
sys.path.insert(0, str(ROOT / "correlator"))
try:
    from correlate import label_for, parse_ts
except Exception:                       # correlator missing: the UI still starts
    label_for = parse_ts = None

ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
STEP = re.compile(r"^==\s*(\d+)/(\d+)\s+(.*)$")

app = FastAPI(title="HiveWatch control room")

# ---------------------------------------------------------------- run state
run = {"mode": "demo", "state": "idle", "step": 0, "total": 8, "title": "", "lines": [],
       "started": None, "ended": None, "exit": None}
lock = threading.Lock()


def _reader(proc):
    for raw in proc.stdout:
        line = ANSI.sub("", raw.rstrip("\n"))
        with lock:
            run["lines"].append(line)
            m = STEP.match(line)
            if m:
                run["step"], run["total"], run["title"] = int(m.group(1)), int(m.group(2)), m.group(3).strip()
    code = proc.wait()
    with lock:
        run["exit"] = code
        run["ended"] = time.time()
        run["state"] = "done" if code == 0 else "failed"
        if code == 0:
            run["step"] = run["total"]


def _start(cmd, mode="demo"):
    with lock:
        if run["state"] == "running":
            raise HTTPException(409, "A run is already in progress. Wait for it to finish.")
        run.update(mode=mode, state="running", step=0, title="Starting", lines=[], started=time.time(), ended=None, exit=None)
    try:
        proc = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, bufsize=1)
    except OSError as e:
        with lock:
            run.update(state="failed", ended=time.time(), exit=-1)
            run["lines"].append(f"FAILED: could not start {cmd[0]}: {e}")
        return
    threading.Thread(target=_reader, args=(proc,), daemon=True).start()


@app.post("/api/run")
def start_run():
    _start(["bash", "scripts/run_demo.sh"], "demo")
    return {"ok": True}


@app.post("/api/compare")
def start_compare():
    _start(["bash", "scripts/compare_identity.sh"], "compare")
    return {"ok": True}


@app.post("/api/reset")
def reset_lab():
    _start(["docker", "compose", "down"], "reset")
    return {"ok": True}


def _version(txt):
    m = re.search(r"^\d+/tcp\s+\S+\s+\S+\s+(.*)$", txt or "", re.M)
    return m.group(1).strip() if m else None


@app.get("/api/compare")
def compare_result():
    d = OUT / "compare"
    res = {"available": False}
    for k in ("before", "after"):
        t, e = d / f"{k}.txt", d / f"{k}.env"
        if not t.exists():
            continue
        env = {}
        if e.exists():
            for ln in e.read_text().splitlines():
                if "=" in ln:
                    a, b = ln.split("=", 1)
                    env[a] = b
        raw = t.read_text(errors="replace")
        res[k] = {"raw": raw, "version": _version(raw), "hostname": env.get("HP_HOSTNAME"), "banner": env.get("HP_BANNER")}
    res["available"] = "before" in res and "after" in res
    return res


@app.get("/api/run")
def run_state():
    with lock:
        return {k: run[k] for k in ("mode", "state", "step", "total", "title", "started", "ended", "exit")} | {"lines": len(run["lines"])}


@app.get("/api/run/stream")
def stream(since: int = 0):
    def gen():
        i = since
        while True:
            with lock:
                chunk, st = run["lines"][i:], run["state"]
                meta = {"mode": run["mode"], "state": st, "step": run["step"], "total": run["total"], "title": run["title"]}
            for line in chunk:
                yield f"data: {json.dumps({'line': line, **meta})}\n\n"
            i += len(chunk)
            if not chunk:
                yield f"data: {json.dumps({'ping': True, **meta})}\n\n"
                if st in ("done", "failed") and i >= len(run["lines"]):
                    return
            time.sleep(0.3)
    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ---------------------------------------------------------------- lab status
@app.get("/api/status")
def status():
    containers = []
    try:
        r = subprocess.run(["docker", "compose", "ps", "-a", "--format", "json"], cwd=ROOT,
                           capture_output=True, text=True, timeout=15)
        for ln in r.stdout.splitlines():
            ln = ln.strip()
            if ln.startswith("{"):
                d = json.loads(ln)
                containers.append({"name": d.get("Service") or d.get("Name"), "state": d.get("State"),
                                   "status": d.get("Status")})
        docker_ok = r.returncode == 0
    except Exception:
        docker_ok = False
    env = {}
    envf = ROOT / ".env"
    if envf.exists():
        for ln in envf.read_text().splitlines():
            if "=" in ln and not ln.lstrip().startswith("#"):
                k, v = ln.split("=", 1)
                env[k.strip()] = v.strip()
    return {"docker": docker_ok, "containers": containers,
            "hostname": env.get("HP_HOSTNAME"), "banner": env.get("HP_BANNER")}


# ---------------------------------------------------------------- results
def _json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return default


@app.get("/api/results")
def results():
    sessions = _json(OUT / "sessions.json", None)
    if sessions is None:
        return {"available": False}
    scen = []
    sj = OUT / "scenarios.jsonl"
    if sj.exists():
        for ln in sj.read_text().splitlines():
            if ln.strip():
                scen.append(json.loads(ln))
    for s in sessions:
        s["scenario"] = "-"
        if scen and label_for and parse_ts:
            try:
                s["scenario"] = label_for(parse_ts(s["start"]), scen)
            except Exception:
                pass
    counts = {"matched": 0, "partial": 0, "unmatched": 0}
    for s in sessions:
        counts[s.get("status", "unmatched")] = counts.get(s.get("status", "unmatched"), 0) + 1
    per = {}
    for s in sessions:
        d = per.setdefault(s["scenario"], {"sessions": 0, "commands": 0, "failed_logins": 0})
        d["sessions"] += 1
        d["commands"] += len([c for c in s.get("commands", []) if c])
        d["failed_logins"] += s.get("failed_logins", 0)
    pcaps = sorted((ROOT / "data" / "pcap").glob("*.pcap"))
    logs = {}
    for p in sorted((OUT / "scenario_logs").glob("*.txt")) if (OUT / "scenario_logs").exists() else []:
        logs[p.stem] = p.read_text(errors="replace")
    nm = logs.get("01_nmap_scan", "")
    m = re.search(r"^\d+/tcp\s+\S+\s+\S+\s+(.*)$", nm, re.M)
    return {"available": True, "sessions": sessions, "counts": counts, "per_scenario": per,
            "pcap_only": _json(OUT / "pcap_only.json", []), "scenario_logs": logs,
            "nmap_version": m.group(1).strip() if m else None,
            "pcap": pcaps[-1].name if pcaps else None,
            "updated": max((p.stat().st_mtime for p in OUT.glob("sessions.json")), default=None)}


@app.get("/api/download/{name}")
def download(name: str):
    allowed = {"sessions.json", "sessions.csv", "pcap_only.json"}
    if name not in allowed:
        raise HTTPException(404)
    p = OUT / name
    if not p.exists():
        raise HTTPException(404, "Run the demo first.")
    return FileResponse(p, filename=name)


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("PORT", 8000)), log_level="warning")
