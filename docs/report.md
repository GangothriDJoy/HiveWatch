# HiveWatch — Phase 1 Project Report

## 1. Project Overview

HiveWatch is a controlled SSH honeypot lab designed to observe simulated attacker activity and connect application-level events with network traffic. The Phase 1 prototype combines Cowrie, packet capture, simulated attacker scenarios, and a session-to-packet correlation module.

The system runs using Docker Compose. The attacker container executes predefined scenarios against the honeypot within the lab network. Cowrie records SSH interaction events, while the capture service records network traffic in PCAP files. The correlation module uses session information, including source IP, source port, and time, to associate Cowrie sessions with packet flows.

## 2. Architecture and Components

- **Cowrie honeypot:** Emulates an SSH service and records attacker interactions in JSON logs.
- **Capture service:** Records network traffic into timestamped PCAP files for inspection.
- **Attacker container:** Runs the Nmap scan, Hydra login-testing scenario, and manual SSH scenario.
- **Hostname/banner randomizer:** Selects hostname and SSH banner values from configuration pools and writes them to the environment configuration used by the Compose setup.
- **Correlation module:** Compares Cowrie sessions with packet-capture data and reports matched, partial, and unmatched results.
- **Evidence and reporting:** Stores test results, packet-capture validation, and session evidence for review.

## 3. Hostname and Banner Randomization

The randomizer is implemented in `randomizer/randomize.py`, with candidate values maintained in `config/hostname_pool.json` and `config/banner_pool.json`. The selected values are written to `.env`, which is used to configure the Cowrie container.

After changing the values, the relevant container must be recreated for the configuration to take effect. The Nmap scenario in `attacker/scenarios/01_nmap_scan.sh` scans SSH port 2222 and records the service information visible to a simulated attacker.

Member 2 implemented the randomizer and configuration pools and recorded before/after Nmap evidence in `docs/evidence/nmap_before_after.txt`. The team's integration checklist also records successful randomizer runs in which Nmap detected a randomized SSH banner.

The purpose of this feature is to vary the honeypot's observable identity between runs. The recorded results demonstrate banner variation; they should not be interpreted as proof that all honeypot fingerprinting techniques are defeated.

## 4. Running the Prototype

Prerequisites include Docker Desktop with its engine running, Ubuntu/WSL, Git, and the project dependencies.

From the project directory:

```bash
cd ~/HiveWatch
source .venv/bin/activate
docker compose up -d
docker compose ps

```
```

To run the complete demonstration pipeline:

```bash
scripts/run_demo.sh
```

To test the hostname and banner randomizer:

```bash
python3 randomizer/randomize.py
docker compose up -d --force-recreate cowrie
sleep 8
docker compose exec -T attacker /scenarios/01_nmap_scan.sh after
```

Follow `docs/demo_script.md` for the full demonstration sequence. The `.env` file contains local configuration and should not be committed.

## 5. Testing and Results

The team's recorded evidence from 10 October 2026 reports the following results:

* **Nmap scan:** SSH port 2222 was detected, with one Cowrie session matched in the recorded scenario test.
* **Hydra login testing:** The scenario completed with exit code 0, and three Cowrie sessions were matched.
* **Manual SSH:** The connection completed successfully, five commands were recorded, and one session was matched.
* **Packet capture:** PCAP files were created and opened successfully. The test checklist records successful capture-stop and port-filter checks.
* **Session correlation:** Recorded full-demo runs reported six matched sessions, zero partial sessions, and zero unmatched Cowrie sessions in the correlation output.
* **Clean-clone test:** The team recorded successful startup of the three containers and successful Nmap and SSH scenarios.
* **PCAP validation:** `docs/evidence/pcap_check.txt` records a readable 14,848-byte capture containing 49 packets. One Cowrie session was found in the PCAP, with none missing.

These results are based on the team's recorded tests and do not imply that every test was repeated while preparing this report.

## 6. Known Limitations

1. Some captured connections did not correspond to Cowrie sessions. They may have been probes that did not complete an SSH handshake, but their exact cause requires further investigation.
2. The capture service reported that promiscuous mode was unsupported on the `any` interface. Capture nevertheless completed in the recorded tests.
3. The clean-clone test required local Docker Compose adjustments to avoid conflicts caused by fixed container and network names.
4. One demo run reported a directory-permission warning. A later recorded run completed without that warning after a permission change.
5. Randomized SSH banners demonstrate variation in the visible service string; they do not guarantee protection against every fingerprinting technique. Hostname changes should also be independently verified.
6. Advanced risk scoring, adaptive login delays, a dashboard, attacker classification, LLM-assisted reporting, and Zeek integration are outside the current Phase 1 prototype.

## 7. Future Work

Future work includes improving deployment repeatability, investigating unmatched connections, independently verifying hostname changes, and strengthening automated tests. Additional features may include risk scoring, adaptive deception, a dashboard, attacker-behavior classification, LLM-assisted reporting, and Zeek integration.

## 8. Conclusion

HiveWatch Phase 1 combines an SSH honeypot, simulated attacker scenarios, packet capture, and session correlation in a controlled lab. The team's recorded evidence demonstrates successful execution of the main scenarios and collection of both Cowrie logs and PCAP files. The randomizer adds variation to the SSH banner visible to a simulated attacker. Further work should focus on repeatable deployment, investigating unmatched connections, and systematically validating anti-fingerprinting behavior.
