#!/usr/bin/env bash
# Removes a WireGuard client peer from the server.
# Run as root on the server: sudo bash remove-client.sh <client-name>

set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "Please run this script as root (e.g. sudo bash remove-client.sh <name>)" >&2
  exit 1
fi

CLIENT_NAME="${1:-}"
if [[ -z "$CLIENT_NAME" ]]; then
  echo "Usage: $0 <client-name>" >&2
  exit 1
fi

WG_DIR="/etc/wireguard"
WG_NIC="wg0"
WG_CONF="${WG_DIR}/${WG_NIC}.conf"
CLIENT_CONF="${WG_DIR}/clients/${CLIENT_NAME}.conf"

if ! grep -q "^# ${CLIENT_NAME}\$" "$WG_CONF"; then
  echo "No client named '${CLIENT_NAME}' found in ${WG_CONF}." >&2
  exit 1
fi

# Delete the [Peer] block that has "# <name>" as its first line
sed -i "/^\[Peer\]\$/{N;/# ${CLIENT_NAME}\$/{N;N;N;d}}" "$WG_CONF"

rm -f "$CLIENT_CONF"

wg syncconf "$WG_NIC" <(wg-quick strip "$WG_NIC")

echo "Client '${CLIENT_NAME}' removed."
