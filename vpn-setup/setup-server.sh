#!/usr/bin/env bash
# Sets up a WireGuard VPN server on Ubuntu/Debian.
# Run as root on the European server: sudo bash setup-server.sh

set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "Please run this script as root (e.g. sudo bash setup-server.sh)" >&2
  exit 1
fi

WG_DIR="/etc/wireguard"
WG_NIC="wg0"
WG_CONF="${WG_DIR}/${WG_NIC}.conf"
WG_PORT="${WG_PORT:-51820}"
WG_SUBNET="10.66.66.0/24"
WG_SERVER_IP="10.66.66.1/24"

if [[ -f "$WG_CONF" ]]; then
  echo "${WG_CONF} already exists. Server appears to be set up already." >&2
  exit 1
fi

PUB_NIC=$(ip route get 1.1.1.1 | awk '{for(i=1;i<=NF;i++) if ($i=="dev") print $(i+1)}' | head -n1)
if [[ -z "$PUB_NIC" ]]; then
  echo "Could not auto-detect the public network interface." >&2
  exit 1
fi

echo "Installing WireGuard and qrencode..."
apt-get update -y
apt-get install -y wireguard qrencode

mkdir -p "$WG_DIR"
chmod 700 "$WG_DIR"
umask 077

SERVER_PRIVATE_KEY=$(wg genkey)
SERVER_PUBLIC_KEY=$(echo "$SERVER_PRIVATE_KEY" | wg pubkey)
echo "$SERVER_PUBLIC_KEY" > "${WG_DIR}/server_public.key"

cat > "$WG_CONF" <<EOF
[Interface]
Address = ${WG_SERVER_IP}
ListenPort = ${WG_PORT}
PrivateKey = ${SERVER_PRIVATE_KEY}
PostUp = iptables -t nat -A POSTROUTING -o ${PUB_NIC} -j MASQUERADE; iptables -A FORWARD -i ${WG_NIC} -j ACCEPT
PostDown = iptables -t nat -D POSTROUTING -o ${PUB_NIC} -j MASQUERADE; iptables -D FORWARD -i ${WG_NIC} -j ACCEPT
EOF
chmod 600 "$WG_CONF"

echo "Enabling IP forwarding..."
if ! grep -q '^net.ipv4.ip_forward=1' /etc/sysctl.conf; then
  echo 'net.ipv4.ip_forward=1' >> /etc/sysctl.conf
fi
sysctl -p >/dev/null

if command -v ufw >/dev/null; then
  echo "Opening UDP port ${WG_PORT} in ufw..."
  ufw allow "${WG_PORT}/udp" >/dev/null || true
fi

echo "Starting WireGuard..."
systemctl enable --now "wg-quick@${WG_NIC}"

PUBLIC_IP=$(curl -s -4 ifconfig.me || true)

cat <<EOF

WireGuard server is up.

  Interface:    ${WG_NIC}
  Server IP:    ${WG_SERVER_IP}
  Listen port:  ${WG_PORT}/udp
  Public key:   ${SERVER_PUBLIC_KEY}
  Public IP:    ${PUBLIC_IP:-<could not detect, check manually>}

Next step: run ./add-client.sh <client-name> to generate a config for your computer.
EOF
