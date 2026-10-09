#!/usr/bin/env bash
# Owner: Member 4   Evidence: docs/evidence/pcap_check.txt (C8)
# Usage: capture/check_pcap.sh <file.pcap> [data/cowrie/cowrie.json]
#
# 1. Opens the pcap and checks it is readable (not cut off).
# 2. Lists the distinct CLIENT ports that connected to port 2222.
#    Every attack session (one SSH login, one Hydra try, one Nmap probe)
#    uses its own client port, so this shows each session really is in the pcap.
# 3. If you also give the Cowrie log, compares: every session in the log
#    must have its client port in the pcap.
# Exit code: 0 = all good, 1 = problem.

PCAP="${1:-}"
LOG="${2:-}"
PORT="${CAPTURE_PORT:-2222}"

if [ -z "$PCAP" ] || [ ! -f "$PCAP" ]; then
  echo "Usage: capture/check_pcap.sh <file.pcap> [cowrie.json]"
  echo "File not found: '$PCAP'"
  exit 1
fi
if ! command -v tcpdump >/dev/null 2>&1; then
  echo "tcpdump is not installed. Run:  sudo apt install -y tcpdump"
  exit 1
fi

echo "=== pcap check: $PCAP ==="
echo "Size: $(stat -c %s "$PCAP") bytes"

# Is the file readable and complete?
ERR=$(tcpdump -nn -r "$PCAP" 2>&1 >/dev/null | grep -i -E "truncated|bad dump|error" || true)
if [ -n "$ERR" ]; then
  echo "WARNING: the file may be cut off: $ERR"
  STATUS=1
else
  echo "File opens cleanly: yes"
  STATUS=0
fi

TOTAL=$(tcpdump -nn -r "$PCAP" 2>/dev/null | wc -l)
TO_HP=$(tcpdump -nn -r "$PCAP" "tcp dst port $PORT" 2>/dev/null | wc -l)
echo "Packets in file: $TOTAL   (client -> honeypot: $TO_HP)"

TMP=$(mktemp)
tcpdump -nn -r "$PCAP" "tcp dst port $PORT" 2>/dev/null \
  | awk '{n=split($3,a,"."); print a[n]}' | sort -n | uniq > "$TMP"
NPORTS=$(wc -l < "$TMP")
echo "Distinct client ports (= connections): $NPORTS"
echo "Ports: $(tr '\n' ' ' < "$TMP")"

if [ -n "$LOG" ]; then
  if [ ! -f "$LOG" ]; then
    echo "Cowrie log not found: $LOG"
    rm -f "$TMP"
    exit 1
  fi
  echo "--- comparing with Cowrie log: $LOG ---"
  python3 - "$LOG" "$TMP" <<'PY'
import json, sys
log, ports_file = sys.argv[1], sys.argv[2]
pcap_ports = set(int(x) for x in open(ports_file).read().split())
sessions = {}
for line in open(log):
    line = line.strip()
    if not line:
        continue
    try:
        e = json.loads(line)
    except ValueError:
        continue
    if e.get("eventid") == "cowrie.session.connect":
        sessions[e["session"]] = int(e["src_port"])
missing = [(s, p) for s, p in sessions.items() if p not in pcap_ports]
print("Cowrie sessions in log : %d" % len(sessions))
print("Found in pcap          : %d" % (len(sessions) - len(missing)))
print("Missing from pcap      : %d" % len(missing))
for s, p in missing:
    print("  MISSING session %s (client port %d)" % (s, p))
sys.exit(1 if missing else 0)
PY
  [ $? -ne 0 ] && STATUS=1
fi

rm -f "$TMP"
[ $STATUS -eq 0 ] && echo "RESULT: PASS" || echo "RESULT: FAIL"
exit $STATUS
