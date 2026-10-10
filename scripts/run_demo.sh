#!/usr/bin/env bash
# Owner: Member 1   Contract: C6, C7
# Usage: scripts/run_demo.sh
#
# One command for the whole demo:
#   randomize -> start Cowrie + capture -> run all scenarios -> stop capture
#   -> archive the Cowrie log -> correlate -> print the session table.
# Pieces that do not exist yet (for example the randomizer) are skipped with a
# clear message, so the script already works today and gets better as members push.

set -u -o pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
ROOT="$(pwd)"

say()  { printf '\n\033[1m== %s\033[0m\n' "$*"; }
die()  { printf '\n\033[31mFAILED: %s\033[0m\n' "$*" >&2; exit 1; }
skip() { printf '   [skipped] %s\n' "$*"; }

# Python for the correlator: the project's virtual environment if it exists.
if [ -x "$ROOT/.venv/bin/python" ]; then PY="$ROOT/.venv/bin/python"; else PY=python3; fi
"$PY" -c "import scapy" 2>/dev/null || die "scapy is not installed. Run: source .venv/bin/activate && pip install scapy"
command -v docker >/dev/null 2>&1 || die "docker not found. Open Docker Desktop and check WSL integration."

# ---- 1. Folders and settings -------------------------------------------------
say "1/8  Prepare folders and .env"
[ -f .env ] || { cp .env.example .env && echo "   created .env from .env.example"; }
mkdir -p data/cowrie data/pcap data/out docs/evidence
# Cowrie runs as user 999 inside its container and must be allowed to write its log here.
chmod 777 data/cowrie

# ---- 2. Randomize hostname and banner ----------------------------------------
say "2/8  Randomize hostname and banner (Member 2)"
if [ -f randomizer/randomize.py ]; then
  "$PY" randomizer/randomize.py || die "randomizer/randomize.py failed"
else
  skip "randomizer/randomize.py not found yet - using the values in .env as they are"
fi

# ---- 3. Start Cowrie and capture together ------------------------------------
say "3/8  Start Cowrie and capture (recreated together)"
docker compose up -d --force-recreate cowrie capture attacker || die "docker compose up failed"
echo -n "   waiting for Cowrie on port 2222 "
ready=0
for i in $(seq 1 40); do
  if docker compose exec -T attacker bash -c 'exec 3<>/dev/tcp/cowrie/2222' 2>/dev/null; then ready=1; break; fi
  echo -n "."; sleep 1
done
echo
[ "$ready" = 1 ] || { docker compose logs --tail 20 cowrie; die "Cowrie did not accept connections within 40 s"; }
sleep 3   # let tcpdump start before the first packet
echo "   Cowrie is up. Capture started:"
docker compose logs --tail 3 capture 2>/dev/null | sed 's/^/   /'

# ---- 4. Attack scenarios ------------------------------------------------------
say "4/8  Run attack scenarios (from inside the lab network)"
shopt -s nullglob
scenarios=(attacker/scenarios/[0-9]*.sh)
[ "${#scenarios[@]}" -gt 0 ] || die "no scenario scripts found in attacker/scenarios/"
mkdir -p data/out/scenario_logs
: > data/out/scenarios.jsonl     # start/end time of every scenario, so results can be labelled
for s in "${scenarios[@]}"; do
  n="$(basename "$s")"
  echo "-- $n"
  t0="$(date +%s.%N)"
  docker compose exec -T attacker "/scenarios/$n" 2>&1 | tee "data/out/scenario_logs/${n%.sh}.txt" || echo "   [warn] $n exited with an error; continuing"
  t1="$(date +%s.%N)"
  printf '{"name": "%s", "start": %s, "end": %s}\n' "$n" "$t0" "$t1" >> data/out/scenarios.jsonl
done
[ -f attacker/scenarios/01_nmap_scan.sh ] || skip "01_nmap_scan.sh not found yet (Member 2)"

# ---- 5. Stop capture cleanly --------------------------------------------------
say "5/8  Stop capture so the pcap file is closed cleanly"
sleep 3   # let the last packets and Cowrie's log lines arrive
docker compose stop capture || die "could not stop capture"
PCAP="$(ls -t data/pcap/*.pcap 2>/dev/null | head -1)"
[ -n "$PCAP" ] || die "no pcap file in data/pcap/"
echo "   pcap: $PCAP ($(stat -c %s "$PCAP") bytes)"

# ---- 6. Cowrie log ------------------------------------------------------------
say "6/8  Check and archive the Cowrie log"
LOG=data/cowrie/cowrie.json
[ -s "$LOG" ] || die "$LOG is missing or empty (is data/cowrie writable for Cowrie?)"
echo "   log: $LOG ($(wc -l < "$LOG") events)"
if [ -x scripts/export_logs.sh ]; then scripts/export_logs.sh; else skip "scripts/export_logs.sh not found"; fi

# ---- 7. Correlate -------------------------------------------------------------
say "7/8  Correlate Cowrie sessions with packet flows"
"$PY" correlator/correlate.py --log "$LOG" --pcap "$PCAP" --out data/out --scenarios data/out/scenarios.jsonl 2>&1 | tee data/out/session_table.txt
[ "${PIPESTATUS[0]}" -eq 0 ] || die "correlator failed"

# ---- 8. Evidence --------------------------------------------------------------
say "8/8  Save evidence"
cp data/out/session_table.txt docs/evidence/session_table.txt
echo "   docs/evidence/session_table.txt"
echo "   data/out/sessions.json  data/out/sessions.csv"
printf '\n\033[32mDone.\033[0m Open %s in Wireshark to show the packets.\n' "$PCAP"
