# HiveWatch Phase 1 - Live demo script (about 10 minutes)

Presenter: Member 1. Review: Monday 12 Oct, 9:00 am.

## Before the review (do this 30 minutes early)

1. Open Docker Desktop and wait until it says "running".
2. Open Ubuntu and run:
   ```
   cd ~/HiveWatch && git pull && source .venv/bin/activate
   docker compose down
   docker compose build attacker
   ```
3. Run the full pipeline once, so you know it works on the day and have fresh evidence:
   ```
   scripts/run_demo.sh
   ```
4. Open `data/pcap/` in Windows Explorer and keep Wireshark ready.
5. Keep one Ubuntu window open at `~/HiveWatch`. Make the font large.

## Part 1 - What it is (1 minute)

"HiveWatch is an SSH honeypot that changes how it looks to attackers. Today we show
Phase 1: the honeypot, the packet capture, and the tool that links the two."

Show the three containers: `docker compose ps`

- cowrie: the honeypot
- capture: records every packet to a pcap file
- attacker: a separate container that plays the attacker, inside the same isolated network

Say: "The lab network is marked internal, so nothing can reach the real internet."

## Part 2 - Before and after: the honeypot changes its identity (3 minutes)

```
docker compose down
cp .env.example .env
docker compose up -d
sleep 8
docker compose exec -T attacker /scenarios/01_nmap_scan.sh before
```
Point at the line `2222/tcp open ssh VERSION ...`. This is what an attacker sees.

Now randomize and restart:
```
python3 randomizer/randomize.py
cat .env
docker compose up -d --force-recreate cowrie capture
sleep 8
docker compose exec -T attacker /scenarios/01_nmap_scan.sh after
```
Point at the new version string. Say: "Same honeypot, different banner and hostname.
An attacker who fingerprinted it yesterday sees something different today."

(Rehearse this part once. If the "before" and "after" strings look the same, run
randomize.py again - the pool can pick the same entry twice.)

## Part 3 - Attack and capture (2 minutes)

Run the whole pipeline:
```
docker compose down
scripts/run_demo.sh
```
While it runs, explain the steps as they scroll:
- step 4: three attacks: Nmap scan, Hydra password guessing, a manual SSH login with 5 commands
- step 5: capture is stopped so the pcap closes cleanly

## Part 4 - The two data sources (2 minutes)

1. Honeypot log (what the attacker did):
   ```
   head -c 1500 data/cowrie/cowrie.json
   ```
2. Packets (what went over the wire): open the newest file in `data/pcap/` in Wireshark,
   type `tcp.port == 2222` in the filter bar.

Say: "Cowrie knows the commands but not the packets. The pcap has the packets but not the
commands. Each alone is incomplete."

## Part 5 - The correlator (my part) (2 minutes)

Show the table printed in step 7 (or `cat docs/evidence/session_table.txt`):

- Every Cowrie session is matched to its packet flow using source IP, source port and time.
- Status: matched / partial / unmatched. All sessions show `matched`.
- The `scenario` column says which attack each session belongs to.
- "Per scenario" counts: Nmap 1, Hydra 3, manual SSH 1 (5 commands).
- Last block: connections that appear in the pcap but have no Cowrie session
  (the readiness check and the Nmap probe). Cowrie never logs those; the packet capture does.
  This is the value of having both sources.

## If something fails during the demo

- Container name conflict: `docker rm -f hivewatch-cowrie hivewatch-capture hivewatch-attacker; docker network rm hivewatch-lab`
- No sessions in the table: `chmod 777 data/cowrie`, then re-run `scripts/run_demo.sh`.
- Backup evidence, already saved: `docs/evidence/` and `data/out/scenario_logs/`.

## What comes next (30 seconds)

Risk scoring, adaptive login delay, dashboard, attacker classifier, LLM report, Zeek.
All of these read the session records the correlator already produces.
