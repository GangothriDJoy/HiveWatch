# HiveWatch

HiveWatch is a controlled SSH honeypot lab for observing simulated attacker activity. It uses Cowrie to record SSH sessions, tcpdump to capture network traffic, and an attacker container to run test scenarios.

## Architecture

The lab contains three Docker Compose services:

- **cowrie** — SSH honeypot listening on port 2222 inside the lab network.
- **capture** — captures TCP traffic involving port 2222 and writes PCAP files.
- **attacker** — provides tools such as Hydra, Nmap, OpenSSH client, and sshpass for controlled testing.

The services use an internal Docker network named `hivewatch-lab`. The attacker container is intended to communicate with the honeypot without external network access.

HiveWatch/
├── attacker/
│   ├── Dockerfile
│   └── scenarios/
├── correlator/
├── data/
│   ├── cowrie/
│   ├── pcap/
│   └── out/
├── docs/
│   └── evidence/
├── randomizer/
├── scripts/
├── .env.example
├── docker-compose.yml
└── README.md

## Requirements

- Docker Desktop with the Docker Compose plugin, or a compatible Docker Engine and Compose installation.
- Git.
- A Linux environment or WSL Ubuntu is recommended.

## Configuration

Optional environment overrides can be configured using `.env`.

Start from the example file:

```bash
cp .env.example .env
```

The example settings are:

```dotenv
HP_HOSTNAME=svr04
HP_BANNER=SSH-2.0-OpenSSH_9.2p1 Debian-2+deb12u3
```

Do not commit `.env`, generated logs, or packet captures to Git.

## Start the lab

Create the required data directories:

```bash
mkdir -p data/cowrie data/pcap data/out
```

Build the attacker image:

```bash
docker compose build attacker
```

Start Cowrie and the attacker container:

```bash
docker compose up -d cowrie attacker
```

Start packet capture after Cowrie is running:

```bash
docker compose up -d capture
```

Check the status of all services:

```bash
docker compose ps
```

## Run the Hydra scenario

Run the controlled SSH login test against the Cowrie honeypot:

```bash
docker compose exec -T attacker /scenarios/02_hydra_bruteforce.sh
```

The scenario uses the target host and port configured for the attacker service. It prints one summary line and exits with status `0` when the scenario finishes, including when login attempts fail. Detailed Hydra output is saved inside the attacker container.

Run attack simulations only against the isolated lab you control.

## Inspect Cowrie logs

Cowrie's JSON Lines log is stored at:

```text
data/cowrie/cowrie.json
```

View recent authentication events:

```bash
grep -iE 'login|auth|password' data/cowrie/cowrie.json | tail -n 15
```

Export a timestamped copy of the current log:

```bash
./scripts/export_logs.sh
```

Exported files are written to `data/out/`.

## Inspect packet captures

PCAP files are stored in:

```text
data/pcap/
```

List available captures:

```bash
ls -lh data/pcap/
```

To read packets from a capture, replace the example filename below with an existing PCAP filename. Run this while the capture container is running:

```bash
docker compose exec capture tcpdump -nn -r /pcap/hw-YYYYMMDD-HHMMSS.pcap 'tcp port 2222'
```

Stop the capture service to close the current capture cleanly:

```bash
docker compose stop capture
```

Start it again to begin a new capture file:

```bash
docker compose up -d capture
```

## Verify network isolation

Check that the attacker can reach Cowrie internally:

```bash
docker compose exec -T attacker bash -lc \
  'if timeout 5 bash -c "</dev/tcp/cowrie/2222" 2>/dev/null; then echo "PASS: Cowrie reachable"; else echo "FAIL: Cowrie unreachable"; fi'
```

Test an external TCP connection:

```bash
docker compose exec -T attacker bash -lc \
  'if timeout 5 bash -c "</dev/tcp/1.1.1.1/443" 2>/dev/null; then echo "FAIL: external TCP reachable"; else echo "PASS: external TCP blocked or unreachable"; fi'
```

The external test checks one endpoint only; it does not independently prove that every possible external destination is unreachable. The lab's Docker Compose network is configured with `internal: true`. See `docs/evidence/isolation_proof.txt` for the recorded test results.


## Stop the lab

Stop all services:

```bash
docker compose down
```

This stops and removes the containers and Compose network. Files stored in the project's bind-mounted `data/` directories remain on the host.

## Project data and Git

Generated logs, PCAP files, `.env`, and virtual environments should remain untracked. Check `.gitignore` before staging or committing changes.

## Current implementation scope

The current lab supports Cowrie SSH session logging, packet capture on TCP port 2222, a controlled Hydra test scenario, and a log-export helper. Additional components should be integrated according to the team's parallel build plan and integration contracts.
