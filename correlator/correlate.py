#!/usr/bin/env python3
"""HiveWatch correlator (Member 1).

Reads a Cowrie JSON log + a pcap, matches each Cowrie session to its TCP flow,
and writes data/out/sessions.json and sessions.csv.

Match key: (src_ip, src_port, dst_port) + a time window.
Status: matched | partial | unmatched. Sessions are never dropped.
"""
import argparse
import csv
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from scapy.all import IP, TCP, PcapReader  # pip install scapy


def parse_ts(s):
    """Cowrie timestamps are ISO8601 UTC, e.g. 2026-10-05T10:00:00.123456Z"""
    return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


# ---------- 1. Cowrie log ----------
def parse_cowrie(log_path):
    sessions = defaultdict(lambda: {
        "session_id": None, "src_ip": None, "src_port": None, "dst_port": None,
        "start": None, "end": None, "duration_ms": None,
        "failed_logins": 0, "commands": [],
    })
    bad_lines = 0
    with open(log_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                bad_lines += 1          # log it, do not crash
                continue
            sid = ev.get("session")
            if not sid:
                continue
            s = sessions[sid]
            s["session_id"] = sid
            s["src_ip"] = s["src_ip"] or ev.get("src_ip")
            eid = ev.get("eventid", "")
            ts = parse_ts(ev["timestamp"]) if "timestamp" in ev else None
            if eid == "cowrie.session.connect":
                s["src_port"] = ev.get("src_port")
                s["dst_port"] = ev.get("dst_port")
                s["start"] = ts
            elif eid == "cowrie.login.failed":
                s["failed_logins"] += 1
            elif eid == "cowrie.command.input":
                s["commands"].append(ev.get("input"))
            elif eid == "cowrie.session.closed":
                s["end"] = ts
                s["duration_ms"] = ev.get("duration_ms", ev.get("duration"))
            if ts is not None:
                s["start"] = ts if s["start"] is None else min(s["start"], ts)
    if bad_lines:
        print(f"[warn] {bad_lines} unparseable log line(s) skipped", file=sys.stderr)
    return list(sessions.values())


# ---------- 2. Pcap flows ----------
def pick_pcap(path):
    """A file is used as is. A folder gives its newest *.pcap."""
    p = Path(path)
    if p.is_dir():
        files = sorted(p.glob("*.pcap"), key=lambda f: f.stat().st_mtime)
        if not files:
            sys.exit(f"[error] no .pcap files in {p}")
        print(f"[info] using newest pcap: {files[-1]}", file=sys.stderr)
        return files[-1]
    if not p.is_file():
        sys.exit(f"[error] pcap not found: {p}")
    return p


def extract_flows(pcap_path, server_ports):
    """Return {(client_ip, client_port, server_port): {first, last, packets, bytes}}.
    Works for Ethernet and for Linux cooked captures (tcpdump -i any).
    A cut-off file is read as far as possible and a warning is printed."""
    flows = {}
    try:
        with PcapReader(str(pcap_path)) as pkts:
            for p in pkts:
                if IP not in p or TCP not in p:
                    continue
                ip, tcp = p[IP], p[TCP]
                if tcp.dport in server_ports:
                    key = (ip.src, tcp.sport, tcp.dport)
                elif tcp.sport in server_ports:
                    key = (ip.dst, tcp.dport, tcp.sport)
                else:
                    continue
                t = float(p.time)
                fl = flows.setdefault(key, {"first": t, "last": t, "packets": 0, "bytes": 0})
                fl["first"] = min(fl["first"], t)
                fl["last"] = max(fl["last"], t)
                fl["packets"] += 1
                fl["bytes"] += len(p)
    except Exception as e:  # truncated or unreadable tail
        print(f"[warn] pcap read stopped early ({type(e).__name__}: {e}); "
              f"using the {sum(f['packets'] for f in flows.values())} packets read", file=sys.stderr)
    return flows


def filter_to_pcap_range(sessions, flows, window):
    """Cowrie keeps appending to one log, but each run has its own pcap.
    Keep only sessions that started inside the pcap's time range (+/- window).
    If the pcap has no packets for the honeypot port, keep everything,
    so a failed capture shows up as 'unmatched' instead of disappearing."""
    if not flows:
        return sessions, 0
    t_min = min(f["first"] for f in flows.values()) - window
    t_max = max(f["last"] for f in flows.values()) + window
    kept = [s for s in sessions if s["start"] is not None and t_min <= s["start"] <= t_max]
    return kept, len(sessions) - len(kept)


# ---------- 3. Matching ----------
def correlate(sessions, flows, window):
    out = []
    for s in sessions:
        key = (s["src_ip"], s["src_port"], s["dst_port"])
        fl = flows.get(key)
        status, packets, nbytes = "unmatched", 0, 0
        if fl and s["start"] is not None and abs(fl["first"] - s["start"]) <= window:
            status = "matched"
        elif fl:
            status = "partial"          # same 5-tuple part, time outside window
        else:
            # fallback: same IP + server port, flow starts inside the window
            cands = [(k, v) for k, v in flows.items()
                     if k[0] == s["src_ip"] and k[2] == s["dst_port"]
                     and s["start"] is not None
                     and abs(v["first"] - s["start"]) <= window]
            if cands:
                fl = cands[0][1]
                status = "partial"
        if fl:
            packets, nbytes = fl["packets"], fl["bytes"]
        if s["duration_ms"] is not None:
            duration = round(float(s["duration_ms"]) / 1000.0, 3)
        elif s["end"] and s["start"]:
            duration = round(s["end"] - s["start"], 3)
        else:
            duration = None
        out.append({
            "session_id": s["session_id"],
            "src_ip": s["src_ip"],
            "src_port": s["src_port"],
            "start": datetime.fromtimestamp(s["start"], timezone.utc).isoformat() if s["start"] else None,
            "duration": duration,
            "failed_logins": s["failed_logins"],
            "commands": s["commands"],
            "packets": packets,
            "bytes": nbytes,
            "status": status,
        })
        if status != "matched":
            print(f"[warn] session {s['session_id']} is {status}", file=sys.stderr)
    return out


def write_outputs(records, out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "sessions.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
    cols = ["session_id", "src_ip", "src_port", "start", "duration",
            "failed_logins", "commands", "packets", "bytes", "status"]
    with open(out_dir / "sessions.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in records:
            row = dict(r)
            row["commands"] = " | ".join(c for c in r["commands"] if c)
            w.writerow(row)


def print_table(records):
    hdr = f"{'session':<14}{'src_ip':<16}{'port':<7}{'fails':<6}{'cmds':<5}{'pkts':<6}{'status'}"
    print(hdr)
    print("-" * len(hdr))
    for r in records:
        print(f"{str(r['session_id']):<14}{str(r['src_ip']):<16}{str(r['src_port']):<7}"
              f"{r['failed_logins']:<6}{len(r['commands']):<5}{r['packets']:<6}{r['status']}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", required=True, help="Cowrie JSON log")
    ap.add_argument("--pcap", required=True, help="pcap file, or a folder (newest .pcap is used)")
    ap.add_argument("--out", default="data/out")
    ap.add_argument("--window", type=float, default=5.0, help="time window in seconds")
    ap.add_argument("--all-sessions", action="store_true",
                    help="do not drop sessions outside the pcap time range")
    a = ap.parse_args()

    pcap = pick_pcap(a.pcap)
    sessions = parse_cowrie(a.log)
    # honeypot port(s) come from the log itself, no guessing
    server_ports = {s["dst_port"] for s in sessions if s["dst_port"]}
    flows = extract_flows(pcap, server_ports)
    skipped = 0
    if not a.all_sessions:
        sessions, skipped = filter_to_pcap_range(sessions, flows, a.window)
    records = correlate(sessions, flows, a.window)
    write_outputs(records, a.out)
    print_table(records)
    counts = {k: sum(1 for r in records if r["status"] == k) for k in ("matched", "partial", "unmatched")}
    print(f"\nSummary: {counts['matched']} matched, {counts['partial']} partial, "
          f"{counts['unmatched']} unmatched"
          + (f"  ({skipped} older session(s) outside this pcap's time range were skipped)" if skipped else ""))


if __name__ == "__main__":
    main()
