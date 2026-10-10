#!/usr/bin/env bash
# Owner: Member 1
# Shows the honeypot's identity BEFORE and AFTER randomization, as an attacker's Nmap scan sees it.
# Output: data/out/compare/{before,after}.txt and {before,after}.env  (read by the web UI)
set -u -o pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
if [ -x .venv/bin/python ]; then PY=.venv/bin/python; else PY=python3; fi
say()  { printf '\n== %s  %s\n' "$1" "$2"; }
die()  { printf '\nFAILED: %s\n' "$*" >&2; exit 1; }
OUTD=data/out/compare; mkdir -p "$OUTD" data/cowrie data/pcap data/out; chmod 777 data/cowrie
rm -f "$OUTD"/*

wait_cowrie() {
  for i in $(seq 1 40); do
    docker compose exec -T attacker bash -c 'exec 3<>/dev/tcp/cowrie/2222' 2>/dev/null && { sleep 2; return 0; }
    sleep 1
  done
  return 1
}
scan() {   # $1 = before|after
  docker compose exec -T attacker nmap -n -sV -p 2222 cowrie 2>&1 | tee "$OUTD/$1.txt"
  grep -E '^HP_(HOSTNAME|BANNER)=' .env > "$OUTD/$1.env"
}

say "1/5" "Start the honeypot with its original identity"
[ -f .env.example ] || die ".env.example is missing"
cp .env.example .env
docker compose up -d --force-recreate cowrie capture attacker || die "docker compose up failed"
wait_cowrie || die "Cowrie did not accept connections within 40 s"

say "2/5" "Scan it as an attacker would (before)"
scan before

say "3/5" "Pick a new hostname and SSH version"
[ -f randomizer/randomize.py ] || die "randomizer/randomize.py not found"
old="$(grep '^HP_BANNER=' .env.example)"
for try in 1 2 3 4 5 6; do
  "$PY" randomizer/randomize.py || die "randomizer failed"
  [ "$(grep '^HP_BANNER=' .env)" != "$old" ] && break
  echo "   same banner as before, picking again"
done

say "4/5" "Restart the honeypot with the new identity"
docker compose up -d --force-recreate cowrie capture || die "docker compose up failed"
wait_cowrie || die "Cowrie did not accept connections within 40 s"

say "5/5" "Scan it again (after)"
scan after
echo; echo "Done."
