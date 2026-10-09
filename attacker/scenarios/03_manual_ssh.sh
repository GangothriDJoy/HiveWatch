#!/usr/bin/env bash
# Owner: Member 4   Contract: C4
# Usage: docker compose exec -T attacker /scenarios/03_manual_ssh.sh
#
# Acts like a person: logs in over SSH and types a few commands slowly.
# Settings (environment variables):
#   TARGET_HOST (default cowrie)   TARGET_PORT (default 2222)
#   SSH_USER    (default root)     SSH_PASS    (default hivewatch123)
# Prints ONE summary line and always exits 0, even if the login fails.
# Needs in the attacker image: bash, openssh-client, sshpass.

TARGET_HOST="${TARGET_HOST:-cowrie}"
TARGET_PORT="${TARGET_PORT:-2222}"
SSH_USER="${SSH_USER:-root}"
SSH_PASS="${SSH_PASS:-hivewatch123}"
START="$(date -u +%H:%M:%S)"

if ! command -v sshpass >/dev/null 2>&1; then
  echo "03_manual_ssh: sshpass not found in this container (ssh_exit=127)"
  exit 0
fi

# The commands are typed one by one with pauses, like a human.
(
  sleep 2
  echo "ls"
  sleep 1
  echo "whoami"
  sleep 1
  echo "uname -a"
  sleep 1
  echo "cat /etc/passwd"
  sleep 1
  echo "exit"
) | sshpass -p "$SSH_PASS" ssh -tt \
      -o StrictHostKeyChecking=no \
      -o UserKnownHostsFile=/dev/null \
      -o ConnectTimeout=10 \
      -p "$TARGET_PORT" "$SSH_USER@$TARGET_HOST" >/dev/null 2>&1
RC=$?

echo "03_manual_ssh: target=$TARGET_HOST:$TARGET_PORT user=$SSH_USER ssh_exit=$RC started=$START UTC"
exit 0
