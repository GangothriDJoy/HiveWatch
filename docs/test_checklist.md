# HiveWatch test checklist

Owner: Member 4. Fill this in after every integration window and every full run.
Write PASS or FAIL, the time, your initials, and one line of notes. Never leave a FAIL without a note.

## A. Integration windows

| When | Who | Check | Pass criteria | Result | Time | Notes |
|---|---|---|---|---|---|---|
| Tue 17:30 | Everyone | Stubs pushed | `git pull` shows every stub; each runs and exits 0 | | | |
| Wed 16:00 | M3 + M4 | Compose runs real capture | `docker compose up -d` starts 3 services; after one SSH session `data/pcap/` has a non-empty pcap | | | |
| Wed 16:00 | M3 + M4 | Clean stop | `docker compose stop capture` leaves a file that `tcpdump -nn -r` opens with no error | | | |
| Wed 16:30 | M3 + M2 | Randomizer feeds compose | `.env` written; Cowrie recreated; Nmap shows the new hostname and banner; 3 different picks in a row | | | |
| Wed 17:00 | M1 + M4 | Correlator on compose run | Sessions from the manual SSH scenario show status `matched` | | | |
| Wed 18:00 | Everyone | Full manual run | All three scenarios run in order; results in section B | | | |
| Thu morning | M1 | One command | `scripts/run_demo.sh` works 3 times in a row from a clean clone | | | |
| Thu 12:00 | Everyone | Freeze | Only bug fixes from now on | | | |

## B. Per scenario (fill after each full run)

Use `capture/check_pcap.sh data/pcap/<file>.pcap data/cowrie/cowrie.json` for the pcap columns.

| Scenario | Sessions in Cowrie log | Client ports in pcap | Missing from pcap | Packets dropped | Correlator: matched / partial / unmatched | Result | Notes |
|---|---|---|---|---|---|---|---|
| 01 Nmap scan | | | | | | | |
| 02 Hydra brute force | | | | | | | |
| 03 Manual SSH | | | | | | | |

## C. Capture checks

| Check | How to check | Result | Notes |
|---|---|---|---|
| File name format | File is called `hw-YYYYMMDD-HHMMSS.pcap` in `data/pcap/` | | |
| One new file per capture start | Start capture twice; two different files appear | | |
| Clean stop | `docker compose stop capture`; `docker compose logs capture` shows "0 packets dropped by kernel"; file opens | | |
| Only port 2222 recorded | `tcpdump -nn -r <file>` shows only port 2222 | | |
| Survives a Cowrie restart | After `docker compose up -d --force-recreate cowrie`, a new SSH session appears in a pcap | | |

## D. Known limits found during testing

(Write them here as you find them. They go into the report.)

-

## E. Compose integration test — 10 October 2026

| Check | Result | Notes |
|---|---|---|
| Cowrie, capture, and attacker started | PASS | All three containers running |
| Manual SSH scenario | PASS | `ssh_exit=0`; commands executed |
| Cowrie JSON logging | PASS | JSON session log generated |
| PCAP capture and readability | PASS | 14,593 bytes; 47 packets |
| Session-to-PCAP comparison | PASS | 1 session found; 0 missing |
| Overall validation | PASS | `capture/check_pcap.sh` passed |

**Note:** Fixed client-port extraction in `capture/check_pcap.sh` to handle the `LINUX_SLL2` `tcpdump` output format.
