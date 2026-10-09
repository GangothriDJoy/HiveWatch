#!/bin/sh
# Owner: Member 4   Contract: C3
# Usage: capture.sh
#
# Records TCP port 2222 (both directions) into
#   data/pcap/hw-YYYYMMDD-HHMMSS.pcap      (UTC time in the name)
# One new file every time this script starts.
# Inside the capture container the folder is /data/pcap
# (docker-compose mounts ./data/pcap there).
#
# Optional settings (environment variables):
#   CAPTURE_IFACE  network card to listen on   (default eth0)
#   CAPTURE_PORT   port to record              (default 2222)
#   OUT_DIR        where to save the pcap      (default /data/pcap)

set -eu

IFACE="${CAPTURE_IFACE:-eth0}"
PORT="${CAPTURE_PORT:-2222}"
OUT_DIR="${OUT_DIR:-/data/pcap}"

mkdir -p "$OUT_DIR"
FILE="$OUT_DIR/hw-$(date -u +%Y%m%d-%H%M%S).pcap"

echo "[capture] interface=$IFACE port=$PORT file=$FILE"

# exec = tcpdump becomes the main program, so "docker compose stop capture"
# reaches it directly and it closes the file cleanly.
# -nn  numbers only      -U  write every packet immediately
# -s 0 whole packets     -Z root  avoid permission errors on the shared folder
# -B 4096 big buffer so fast attacks (Hydra) do not drop packets
exec tcpdump -i "$IFACE" -nn -U -s 0 -B 4096 -Z root -w "$FILE" "tcp port $PORT"
