# PyMesh - Zero-Trust Private Mesh Networking

PyMesh is a zero-trust, private encrypted mesh networking platform connecting PCs, VPS instances, servers, containers, and remote subnets across NATs and firewalls.

Created by **MrHat** ([GitHub Profile](https://github.com/mrr-hatt/)). Official repository: [https://github.com/mrr-hatt/pymesh](https://github.com/mrr-hatt/pymesh).

PyMesh pairs native kernel WireGuard for data-plane packet encryption with Python for control-plane coordination, dynamic NAT discovery, zero-decryption UDP relaying, Magic DNS, local TCP port forwarding, access control (ACL) enforcement, and dynamic valid subnet re-allocation.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Key Capabilities](#key-capabilities)
3. [Installation & Requirements](#installation--requirements)
4. [Deployment Tutorial](#deployment-tutorial)
   - [Step 1: Start the Controller Server](#step-1-start-the-controller-server)
   - [Step 2: Start a Relay Server (Optional)](#step-2-start-a-relay-server-optional)
   - [Step 3: Register Nodes](#step-3-register-nodes)
   - [Step 4: Activate Mesh Interfaces](#step-4-activate-mesh-interfaces)
   - [Step 5: Run Network Diagnostics](#step-5-run-network-diagnostics)
5. [Advanced Features](#advanced-features)
   - [Dynamic Subnet Re-allocation & Auto Node Sync](#dynamic-subnet-re-allocation--auto-node-sync)
   - [Local Port Forwarding & Proxy](#local-port-forwarding--proxy)
   - [Subnet Routers & Exit Nodes](#subnet-routers--exit-nodes)
   - [Magic DNS (*.mesh)](#magic-dns-mesh)
   - [Access Control Lists (ACLs)](#access-control-lists-acls)
   - [NAT Traversal & UDP Relaying](#nat-traversal--udp-relaying)
6. [System Boot Reconnection & Persistence](#system-boot-reconnection--persistence)
7. [Version Releases & Upgrade Guide](#version-releases--upgrade-guide)
8. [CLI Command Reference](#cli-command-reference)
9. [Controller REST API Reference](#controller-rest-api-reference)
10. [Testing & Verification](#testing--verification)
11. [Developer & License](#developer--license)

---

## Architecture Overview

```
                         +----------------------+
                         |   PYMESH CONTROLLER  |
                         |                      |
                         | FastAPI REST Server  |
                         | SQLite / PostgreSQL  |
                         | Node Registry & IP   |
                         | Subnet Re-allocator  |
                         | ACL & Subnet Routes  |
                         +----------+-----------+
                                    |
                         HTTPS / JSON Heartbeat
                                    |
       +----------------------------+----------------------------+
       |                            |                            |
       v                            v                            v
+--------------+             +--------------+             +--------------+
|   CLIENT-PC  |             |    VPS-DE    |             |    SERVER    |
|  100.64.0.2  |<----------->|  100.64.0.3  |<----------->|  100.64.0.4  |
+------+-------+             +--------------+             +--------------+
       |
  TUN Interface (pymesh0)
       |
  WireGuard (X25519 / ChaCha20-Poly1305)
       |
  Encrypted P2P UDP / STUN Hole Punch / Relay Fallback
```

---

## Key Capabilities

- **Cryptographic Node Identity**: Every node generates an Ed25519 identity keypair and an X25519 WireGuard keypair upon initialization.
- **Dynamic Subnet Re-allocation**: Change the network IPv4/IPv6 CIDR (e.g. `10.200.0.0/16`) on the fly. The server validates CIDR syntax and automatically instructs all nodes to re-address their local TUN interfaces and update WireGuard peer allowed IPs.
- **Local Port Forwarding**: Expose remote services running on any node directly on `http://localhost:port` of your local host (`pymesh forward <node> <ports>`).
- **NAT Traversal & UDP Hole Punching**: Integrated STUN client (RFC 5389) discovers public reflexive endpoints and initiates simultaneous UDP hole punching bursts.
- **Zero-Decryption UDP Relay**: Encrypted relay servers (`pymesh-relay`) forward framed WireGuard traffic when firewalls prevent direct P2P connections.
- **Magic DNS**: Local UDP DNS server resolves hostnames ending in `.mesh` (e.g. `vps-de.mesh`) directly to CGNAT addresses.
- **Subnet Routing**: Allows designated nodes to act as gateways, exposing remote private subnets across the mesh.

---

## Installation & Requirements

### System Requirements
- Operating System: Linux (with WireGuard kernel module or wireguard-tools support)
- Python: Version 3.10 or higher
- System Privileges: `sudo` / `CAP_NET_ADMIN` required for TUN interface creation

### Environment Setup

```bash
# Clone the repository
git clone https://github.com/mrr-hatt/pymesh.git
cd pymesh

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies via requirements.txt
pip install -r requirements-dev.txt

# Install package in editable mode
pip install -e .
```

---

## Deployment Tutorial

### Step 1: Start the Controller Server

```bash
python -m controller.app
```

### Step 2: Start a Relay Server (Optional)

```bash
python -m relay.app 51830
```

### Step 3: Register Nodes

```bash
pymesh join http://45.90.99.106:8000 --hostname client-pc
```

### Step 4: Activate Mesh Interfaces

```bash
pymesh up
```

### Step 5: Run Network Diagnostics

```bash
pymesh netcheck
```

---

## Advanced Features

### Dynamic Subnet Re-allocation & Auto Node Sync

Change the global mesh IP pool dynamically:

```bash
curl -X PUT "http://localhost:8000/api/v1/network/subnet?ipv4_prefix=10.200.0.0/16"
```

Nodes receive the new subnet prefix on their periodic sync, automatically re-assigning their local `pymesh0` TUN interface IP and syncing WireGuard peers without manual intervention.

### Local Port Forwarding & Proxy

Access remote services hosted locally on any node as if they were running on your localhost:

```bash
# Forward local http://localhost:8000 -> port 8000 on node vps-de
pymesh forward vps-de 8000

# Forward local http://localhost:8080 -> port 3000 on node database
pymesh forward database 8080:3000
```

### Subnet Routers & Exit Nodes

```bash
pymesh route add 10.10.0.0/24 --via vps-de
```

### Magic DNS (*.mesh)

```bash
pymesh ping vps-de
pymesh ssh vps-de
curl http://database.mesh:5432
```

---

## System Boot Reconnection & Persistence

To enable PyMesh to start automatically on system boot via systemd:

```bash
sudo cp pymesh.service /etc/systemd/system/pymesh.service
sudo systemctl daemon-reload
sudo systemctl enable --now pymesh
```

---

## Version Releases & Upgrade Guide

Check your installed PyMesh version:
```bash
pymesh --version
```

### Release Tag History

- **`v0.2.0`**: Dynamic valid subnet CIDR re-allocation with automatic node TUN re-addressing, local TCP port forwarding proxy (`pymesh forward`), systemd boot auto-start persistence, and setuptools 77.0+ Python 3.12 compatibility.
- **`v0.1.0`**: Initial zero-trust private mesh networking release with Ed25519 node identity, WireGuard data plane, STUN hole punching, encrypted UDP relay, and Magic DNS.

### How to Upgrade

```bash
cd pymesh
git pull origin main
source .venv/bin/activate
pip install -e .[dev]
```

---

## CLI Command Reference

| Command | Arguments / Options | Description |
| :--- | :--- | :--- |
| `pymesh --version` | None | Displays current PyMesh version |
| `pymesh join` | `<controller_url> [--token -t] [--hostname -h]` | Registers host identity with PyMesh Controller |
| `pymesh up` | None | Brings up `pymesh0` interface & starts background sync |
| `pymesh down` | None | Deactivates `pymesh0` interface |
| `pymesh status` | None | Displays local node identity, mesh IPs, and status |
| `pymesh nodes` | None | Lists all registered network nodes |
| `pymesh peers` | None | Lists active WireGuard peer connections |
| `pymesh forward` | `<target> <ports>` | Forwards local port over mesh to target node |
| `pymesh netcheck` | None | Runs STUN, NAT classification, and P2P diagnostic suite |
| `pymesh topology` | None | Displays visual tree graph of network topology |
| `pymesh ping` | `<node_or_ip>` | Pings target node across mesh network |
| `pymesh ssh` | `<node_or_ip>` | Opens SSH connection to target node's mesh IP |
| `pymesh route add` | `<subnet> --via <node>` | Configures subnet router gateway |

---

## Controller REST API Reference

| Endpoint | Method | Request Payload | Description |
| :--- | :--- | :--- | :--- |
| `/api/v1/network/subnet` | `PUT` | Query: `ipv4_prefix`, `ipv6_prefix` | Validates & re-allocates network CIDR across all nodes |
| `/api/v1/nodes` | `GET` | None | Lists all registered mesh nodes |
| `/api/v1/nodes/{id}` | `DELETE` | Path: `node_id` | Deletes node registration from controller |
| `/api/v1/network/config` | `GET` | Query: `node_id` | Generates active WireGuard peer configuration |

---

## Developer & License

- **Developer**: **MrHat** ([GitHub Profile](https://github.com/mrr-hatt/))
- **Repository**: [https://github.com/mrr-hatt/pymesh](https://github.com/mrr-hatt/pymesh)
- **License**: MIT License. See [LICENSE](LICENSE) for details.
