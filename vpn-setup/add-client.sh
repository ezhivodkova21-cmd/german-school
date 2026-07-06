#!/usr/bin/env bash
# Generates a WireGuard client config and adds it as a peer on the server.
# Run as root on the server: sudo bash add-client.sh <client-name>

set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "Please run this script as root (e.g. sudo bash add-client.sh <name>)" >&2
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
CLIENTS_DIR="${WG_DIR}/clients"

if [[ ! -f "$WG_CONF" ]]; then
  echo "${WG_CONF} not found. Run setup-server.sh first." >&2
  exit 1
fi

mkdir -p "$CLIENTS_DIR"
chmod 700 "$CLIENTS_DIR"

CLIENT_CONF="${CLIENTS_DIR}/${CLIENT_NAME}.conf"
if [[ -f "$CLIENT_CONF" ]]; then
  echo "A client named '${CLIENT_NAME}' already exists at ${CLIENT_CONF}." >&2
  exit 1
fi

WG_PORT=$(grep -m1 '^ListenPort' "$WG_CONF" | awk -F'= ' '{print $2}')
SERVER_PUBLIC_KEY=$(cat "${WG_DIR}/server_public.key")
PUBLIC_IP=$(curl -s -4 ifconfig.me)

# Find the next free host in 10.66.66.0/24 (server uses .1)
LAST_OCTET=$(grep -oE '10\.66\.66\.[0-9]+' "$WG_CONF" | awk -F'.' '{print $4}' | sort -n | tail -n1)
LAST_OCTET=${LAST_OCTET:-1}
NEXT_OCTET=$((LAST_OCTET + 1))
if [[ "$NEXT_OCTET" -gt 254 ]]; then
  echo "No free addresses left in 10.66.66.0/24." >&2
  exit 1
fi
CLIENT_IP="10.66.66.${NEXT_OCTET}"

CLIENT_PRIVATE_KEY=$(wg genkey)
CLIENT_PUBLIC_KEY=$(echo "$CLIENT_PRIVATE_KEY" | wg pubkey)
CLIENT_PRESHARED_KEY=$(wg genpsk)

cat >> "$WG_CONF" <<EOF

[Peer]
# ${CLIENT_NAME}
PublicKey = ${CLIENT_PUBLIC_KEY}
PresharedKey = ${CLIENT_PRESHARED_KEY}
AllowedIPs = ${CLIENT_IP}/32
EOF

cat > "$CLIENT_CONF" <<EOF
[Interface]
PrivateKey = ${CLIENT_PRIVATE_KEY}
Address = ${CLIENT_IP}/24
DNS = 1.1.1.1

[Peer]
PublicKey = ${SERVER_PUBLIC_KEY}
PresharedKey = ${CLIENT_PRESHARED_KEY}
Endpoint = ${PUBLIC_IP}:${WG_PORT}
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
EOF
chmod 600 "$CLIENT_CONF"

# Apply the new peer without restarting the interface
wg syncconf "$WG_NIC" <(wg-quick strip "$WG_NIC")

echo "Client '${CLIENT_NAME}' created: ${CLIENT_CONF}"
echo
echo "Scan this QR code with the WireGuard mobile app, or copy the file to your computer and import it:"
echo
qrencode -t ansiutf8 < "$CLIENT_CONF"
