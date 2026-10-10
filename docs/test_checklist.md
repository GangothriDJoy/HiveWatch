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
| 01 Nmap scan | 1 | 1 (port 50208) | 0 | 0 overall* | 1 matched / 0 partial / 0 unmatched | PASS | 10 Oct 2026, 13:16 UTC; SSH port 2222 found open |
| 02 Hydra brute force | 3 | 3 (ports 50218, 50234, 50230) | 0 | 0 overall* | 3 matched / 0 partial / 0 unmatched | PASS | 10 Oct 2026, 13:16 UTC; hydra_exit=0 |
| 03 Manual SSH | 1 | 1 (port 50248) | 0 | 0 overall* | 1 matched / 0 partial / 0 unmatched | PASS | 10 Oct 2026, 13:16 UTC; ssh_exit=0; 5 commands recorded |

*Packet drops are reported for the capture as a whole, not separately per scenario. Capture logs reported 0 packets dropped by kernel. The full run had 1 additional matched session outside the three scenario windows and 2 captured connections without corresponding Cowrie sessions.
## C. Capture checks

| Check | How to check | Result | Notes |
|---|---|---|---|
| File name format | File is called `hw-YYYYMMDD-HHMMSS.pcap` in `data/pcap/` | PASS | 10 Oct 2026; timestamped filenames verified |
| One new file per capture start | Start capture twice; two different files appear | PASS | 10 Oct 2026; new file `hw-20261010-133538.pcap` created without overwriting earlier files |
| Clean stop | `docker compose stop capture`; `docker compose logs capture` shows "0 packets dropped by kernel"; file opens | PASS | 10 Oct 2026; capture logs showed 0 packets dropped by kernel; PCAP files opened successfully |
| Only port 2222 recorded | `tcpdump -nn -r <file>` shows only port 2222 | PASS | 10 Oct 2026; filter `not tcp port 2222` returned no packet lines for `hw-20261010-131606.pcap` |
| Survives a Cowrie restart | After restarting Cowrie, a new SSH session appears in a pcap | PASS | 10 Oct 2026; after Cowrie restart, manual SSH succeeded and `hw-20261010-134028.pcap` contained readable TCP traffic on port 2222 |



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

## F. Full demo run — 10 October 2026

| Check | Result | Notes |
|---|---|---|
| Full demo script | PASS | `scripts/run_demo.sh` completed all 8 stages |
| Randomizer | PASS | Selected `HP_HOSTNAME=test-machine` and `HP_BANNER=SSH-2.0-OpenSSH_9.3p2` |
| Nmap scenario | PASS | Scenario exited normally; 1 matched Cowrie session |
| Hydra scenario | PASS | Scenario reported `hydra_exit=0`; 3 matched Cowrie sessions |
| Manual SSH scenario | PASS | `ssh_exit=0`; 1 matched session; 5 commands recorded |
| PCAP capture | PASS | `data/pcap/hw-20261010-130318.pcap`; 29,265 bytes |
| Cowrie JSON log | PASS | `data/cowrie/cowrie.json`; 44 events reported by demo |
| Correlation | PASS | 6 matched, 0 partial, 0 unmatched; 1 older session outside the PCAP time range was skipped |
| Evidence saved | PASS | Session table and sessions JSON/CSV generated |
| Permission warning | NOTE | `chmod` printed `Operation not permitted`, but the demo continued and Cowrie JSON logging succeeded |

**Run notes:** Two captured connections had no corresponding Cowrie session. The correlator identified these as possible port probes or scans that did not complete an SSH handshake. The demo completed despite the permission warning; investigate the warning separately.

## G. Full demo run 2 — 10 October 2026

| Check | Result | Notes |
|---|---|---|
| Full demo script | PASS | All 8 stages completed |
| Directory permission warning | PASS | No `chmod` warning after setting `data/cowrie` to mode 777 |
| Randomizer | PASS | Selected `HP_HOSTNAME=dev-gateway` and `HP_BANNER=SSH-2.0-OpenSSH_8.4p1 Ubuntu-5ubuntu1` |
| Nmap scenario | PASS | 1 matched Cowrie session; randomized SSH banner detected |
| Hydra scenario | PASS | `hydra_exit=0`; 3 matched Cowrie sessions |
| Manual SSH scenario | PASS | `ssh_exit=0`; 1 matched session; 5 commands recorded |
| PCAP capture | PASS | `data/pcap/hw-20261010-131606.pcap`; 29,433 bytes |
| Cowrie JSON log | PASS | `data/cowrie/cowrie.json`; 75 events reported by demo |
| Correlation | PASS | 6 matched, 0 partial, 0 unmatched; 7 older sessions outside the PCAP time range were skipped |
| Evidence saved | PASS | Session table and sessions JSON/CSV generated |

**Run notes:** Two captured connections had no corresponding Cowrie session. The tcpdump warning about promiscuous mode on the `any` interface remained; capture and correlation still completed successfully.
