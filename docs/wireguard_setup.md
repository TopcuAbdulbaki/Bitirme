# WireGuard VPN Setup

Secure network configuration for distributed nodes using WireGuard VPN.

## Overview

```
┌────────────────────────────────────────────────────────────────────┐
│                         INTERNET                                    │
│                                                                     │
│   ┌──────────────┐                                                  │
│   │ Orchestrator │ ◄─── Stable VPS (DigitalOcean/Vultr/etc)        │
│   │  10.0.0.1    │      WireGuard SERVER                            │
│   │  (VPN Hub)   │                                                  │
│   └──────┬───────┘                                                  │
│          │ WireGuard Tunnel (Encrypted)                             │
│          │                                                          │
│    ┌─────┴─────┬─────────────┬─────────────┐                       │
│    │           │             │             │                        │
│    ▼           ▼             ▼             ▼                        │
│ ┌──────┐   ┌──────┐     ┌──────┐     ┌──────┐                      │
│ │Crawlr│   │  DB  │     │ VLM  │     │ LLM  │ ◄── vast.ai rentals  │
│ │10.0. │   │10.0. │     │10.0. │     │10.0. │                      │
│ │0.2   │   │0.3   │     │0.4   │     │0.5   │                      │
│ └──────┘   └──────┘     └──────┘     └──────┘                      │
│  CLIENT     CLIENT       CLIENT       CLIENT                        │
└────────────────────────────────────────────────────────────────────┘
```

## Deployment Strategy

| Component | Where | Why |
|-----------|-------|-----|
| Orchestrator + RabbitMQ | Cheap VPS ($5/mo) | Needs stable IP, always on |
| Crawler | vast.ai or local | Flexible |
| DB | VPS or vast.ai | Needs persistence |
| VLM | vast.ai (GPU) | Needs GPU |
| LLM | vast.ai (GPU) | Needs GPU |

> **Note:** vast.ai machines have dynamic IPs - they connect TO the stable Orchestrator.

---

## IP Assignment

| Node | VPN IP | Port(s) |
|------|--------|---------|
| Orchestrator | 10.0.0.1 | 51820 (WG), 50051 (gRPC), 5672 (RabbitMQ) |
| Crawler | 10.0.0.2 | - |
| DB | 10.0.0.3 | 5432 (PostgreSQL) |
| VLM | 10.0.0.4 | - |
| LLM | 10.0.0.5 | - |

---

## Setup Guide

### Step 1: Orchestrator (VPS) - WireGuard Server

```bash
# Install WireGuard
sudo apt update && sudo apt install wireguard -y

# Generate server keys
cd /etc/wireguard
wg genkey | tee server_private.key | wg pubkey > server_public.key
chmod 600 server_private.key

# Create config
sudo nano /etc/wireguard/wg0.conf
```

**`/etc/wireguard/wg0.conf` (Server):**
```ini
[Interface]
Address = 10.0.0.1/24
ListenPort = 51820
PrivateKey = <server_private_key>

# Enable IP forwarding
PostUp = sysctl -w net.ipv4.ip_forward=1
PostUp = iptables -A FORWARD -i wg0 -j ACCEPT
PostDown = iptables -D FORWARD -i wg0 -j ACCEPT

# Crawler peer
[Peer]
PublicKey = <crawler_public_key>
AllowedIPs = 10.0.0.2/32

# DB peer
[Peer]
PublicKey = <db_public_key>
AllowedIPs = 10.0.0.3/32

# VLM peer
[Peer]
PublicKey = <vlm_public_key>
AllowedIPs = 10.0.0.4/32

# LLM peer
[Peer]
PublicKey = <llm_public_key>
AllowedIPs = 10.0.0.5/32
```

```bash
# Start WireGuard
sudo wg-quick up wg0

# Enable on boot
sudo systemctl enable wg-quick@wg0
```

---

### Step 2: Worker Nodes (vast.ai) - WireGuard Client

**On each vast.ai instance:**

```bash
# Install WireGuard
apt update && apt install wireguard -y

# Generate client keys
cd /etc/wireguard
wg genkey | tee client_private.key | wg pubkey > client_public.key
chmod 600 client_private.key

# Create config
nano /etc/wireguard/wg0.conf
```

**`/etc/wireguard/wg0.conf` (Client - Example for VLM):**
```ini
[Interface]
Address = 10.0.0.4/24
PrivateKey = <vlm_private_key>

[Peer]
PublicKey = <server_public_key>
Endpoint = <orchestrator_public_ip>:51820
AllowedIPs = 10.0.0.0/24
PersistentKeepalive = 25
```

```bash
# Connect
wg-quick up wg0

# Verify
ping 10.0.0.1  # Should reach Orchestrator
```

---

## vast.ai Specific Notes

### Docker Container Setup

vast.ai runs Docker containers. Add WireGuard setup to your startup:

```bash
# In vast.ai instance setup script:
apt update && apt install wireguard -y
echo "<base64_encoded_config>" | base64 -d > /etc/wireguard/wg0.conf
wg-quick up wg0
```

### Pre-generated Configs

For faster deployment, pre-generate configs locally:

```
configs/
├── orchestrator_wg0.conf
├── crawler_wg0.conf
├── db_wg0.conf
├── vlm_wg0.conf
└── llm_wg0.conf
```

Upload correct config when renting each instance.

---

## Local Prototyping

For testing on your local machine:

```
Your PC runs: Orchestrator + Crawler + DB + VLM + LLM
No WireGuard needed - all localhost
```

Use environment variable to switch:
```python
import os

if os.getenv("DEPLOY_MODE") == "production":
    ORCHESTRATOR_IP = "10.0.0.1"  # VPN
else:
    ORCHESTRATOR_IP = "127.0.0.1"  # Local
```

---

## Firewall Rules (Orchestrator VPS)

```bash
# Allow WireGuard
sudo ufw allow 51820/udp

# Allow gRPC (only from VPN)
sudo ufw allow from 10.0.0.0/24 to any port 50051

# Allow RabbitMQ (only from VPN)
sudo ufw allow from 10.0.0.0/24 to any port 5672

# Enable firewall
sudo ufw enable
```

---

## Troubleshooting

| Issue | Check |
|-------|-------|
| Cannot connect to VPN | Is port 51820 open on VPS? |
| Peer not connecting | Is public key correct? |
| Connection drops | Add `PersistentKeepalive = 25` |
| vast.ai restart loses config | Put setup in startup script |

---

## Security Notes

- Never commit private keys to git
- Use environment variables or secrets manager
- Rotate keys if a node is compromised
- Keep Orchestrator VPS updated
