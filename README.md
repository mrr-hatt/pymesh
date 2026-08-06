# PyMesh - Zero-Trust Private Mesh Networking

PyMesh is a zero-trust, private encrypted mesh networking platform that connects PCs, VPS instances, servers, containers, and entire remote subnets across NATs and firewalls.

Created by **MrHat** ([GitHub Profile](https://github.com/mrr-hatt/)). Official repository: [https://github.com/mrr-hatt/pymesh](https://github.com/mrr-hatt/pymesh).

PyMesh pairs WireGuard for kernel data-plane packet encryption with Python for control-plane coordination, dynamic NAT discovery, zero-decryption UDP relaying, Magic DNS, local port forwarding, access control (ACL) enforcement, and an interactive Cisco Packet Tracer-style Web Admin Studio.

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
5. [Cisco Packet Tracer Web Admin Studio](#cisco-packet-tracer-web-admin-studio)
6. [Advanced Features](#advanced-features)
   - [Local Port Forwarding & Proxy](#local-port-forwarding--proxy)
   - [Subnet Routers & Exit Nodes](#subnet-routers--exit-nodes)
   - [Magic DNS (*.mesh)](#magic-dns-mesh)
   - [Access Control Lists (ACLs)](#access-control-lists-acls)
   - [NAT Traversal & UDP Relaying](#nat-traversal--udp-relaying)
7. [System Boot Reconnection & Persistence](#system-boot-reconnection--persistence)
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
                         | ACL & Subnet Routes  |
                         | Web Admin Studio     |
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

PyMesh is structured into two distinct operational planes:

- **Control Plane**: Developed in Python using FastAPI, SQLAlchemy 2.0, and Pydantic v2. Responsible for node identity registration, CGNAT IP allocation (`100.64.0.0/10` IPv4 & `fd00:7079:6d65::/48` IPv6), heartbeat tracking, ACL evaluation, peer discovery, and Web Admin dashboard serving.
- **Data Plane**: Uses native kernel WireGuard (`pyroute2`) for direct peer-to-peer packet encryption and transport. PyMesh configures WireGuard parameters without modifying underlying cryptographic transport protocols.

---

## Key Capabilities

- **Cisco Packet Tracer Web Studio**: Interactive network canvas featuring SVG device nodes, live link indicators, node reprogramming, port forwarding manager, and visual ACL policy matrix.
- **Dynamic Startup Passkey**: Generates a new secure admin passkey on every controller restart, outputting the key directly to the server terminal output.
- **Cryptographic Node Identity**: Every node generates an Ed25519 identity keypair and an X25519 WireGuard keypair upon initialization. Private keys remain strictly on the local host. A deterministic 64-character Node ID is derived from the public key.
- **Automatic Subnet Allocation**: The controller dynamically assigns non-conflicting IP addresses within CGNAT (`100.64.0.0/10`) and IPv6 ULA blocks.
- **NAT Traversal & UDP Hole Punching**: Integrated STUN client (RFC 5389) discovers public reflexive endpoints and initiates simultaneous UDP hole punching bursts for direct P2P reachability.
- **Zero-Decryption UDP Relay**: Encrypted relay servers (`pymesh-relay`) forward framed WireGuard traffic when strict firewalls or Symmetric NATs prevent direct P2P connections.
- **Magic DNS**: Local UDP DNS server resolves hostnames ending in `.mesh` (e.g. `vps-de.mesh`, `database.mesh`) directly to 100.64.0.x CGNAT addresses.
- **Local Port Forwarding**: Expose remote services running on any node directly on `http://localhost:port` of your local host.
- **Subnet Routing**: Allows designated nodes to act as gateways, exposing remote private subnets (e.g., `192.168.1.0/24` or `10.10.0.0/24`) across the mesh.

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

# Install dependencies and package in editable mode
pip install -e .[dev]
```

---

## Deployment Tutorial

### Step 1: Start the Controller Server

The controller manages node registration, peer coordination, and the Web Admin Studio:

```bash
python -m controller.app
```

Upon startup, the controller displays the dynamic admin passkey in the console output:

```text
====================================================================
 [PyMesh Web Admin] Cisco Packet Tracer Dashboard Ready
 [PyMesh Web Admin] Dashboard URL: http://0.0.0.0:8000/net/login
 [PyMesh Web Admin] Passkey:       aB3xK9mP2qR5...
====================================================================
```

To create an authentication join token for node registration (optional):

```bash
curl -X POST "http://localhost:8000/api/v1/auth/join?description=DeployToken"
```

---

### Step 2: Start a Relay Server (Optional)

If some nodes are behind restrictive NATs, launch a relay server on a public host:

```bash
python -m relay.app 51830
```

---

### Step 3: Register Nodes

On each host that will join the mesh network, execute `pymesh join`:

#### On Node 1 (`client-pc`):
```bash
pymesh join http://45.90.99.106:8000 --hostname client-pc
```

#### On Node 2 (`vps-de`):
```bash
pymesh join http://45.90.99.106:8000 --hostname vps-de
```

---

### Step 4: Activate Mesh Interfaces

To activate the `pymesh0` TUN interface and start periodic controller synchronization:

```bash
pymesh up
```

To verify node registration status and peer count:

```bash
pymesh status
```

---

### Step 5: Run Network Diagnostics

Execute `pymesh netcheck` to verify STUN discovery, NAT type, and peer reachability:

```bash
pymesh netcheck
```

---

## Cisco Packet Tracer Web Admin Studio

Open **`http://<controller>:8000/net/login`** in your browser to access the web console.

1. **Authentication**: Enter the startup passkey printed in the controller terminal output.
2. **Interactive Topology Canvas**: View all connected mesh nodes, IP allocations, active WireGuard links, and node states.
3. **Node Reprogramming**: Select any node on the canvas to inspect real-time metrics or rename hostnames.
4. **Port Forwarding Manager**: Add port forwarding rules (`localhost:port -> node:port`) visually from the dashboard.
5. **ACL Policy Matrix**: Define allow/deny rules across developer groups, server tags, or specific node IDs.

---

## Advanced Features

### Local Port Forwarding & Proxy

Access remote services hosted locally on any node as if they were running on your localhost:

```bash
# Forward local http://localhost:8000 -> port 8000 on node vps-de
pymesh forward vps-de 8000

# Forward local http://localhost:8080 -> port 3000 on node database
pymesh forward database 8080:3000
```

### Subnet Routers & Exit Nodes

Expose an internal private network (e.g. `10.10.0.0/24`) through a gateway node (`vps-de`):

```bash
pymesh route add 10.10.0.0/24 --via vps-de
```

### Magic DNS (*.mesh)

PyMesh includes an embedded DNS resolver listening on UDP 5353. It automatically updates local hostname mappings:

```bash
# Ping host by name
pymesh ping vps-de

# SSH into host across mesh
pymesh ssh vps-de

# Query services using .mesh domain
curl http://database.mesh:5432
```

### Access Control Lists (ACLs)

Define security group policies on the controller to restrict inter-node communication:

```json
[
  {
    "source": "group:developers",
    "destination": "group:servers",
    "ports": [22, 443],
    "action": "allow"
  }
]
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

## CLI Command Reference

| Command | Arguments / Options | Description |
| :--- | :--- | :--- |
| `pymesh join` | `<controller_url> [--token -t] [--hostname -h]` | Registers host identity with PyMesh Controller |
| `pymesh up` | None | Brings up `pymesh0` interface & starts background sync |
| `pymesh down` | None | Deactivates `pymesh0` interface |
| `pymesh status` | None | Displays local node identity, mesh IPs, and status |
| `pymesh nodes` | None | Lists all registered network nodes |
| `pymesh peers` | None | Lists active WireGuard peer connections |
| `pymesh forward` | `<target> <ports>` | Forwards local port (e.g. `localhost:8000`) over mesh to target node |
| `pymesh netcheck` | None | Runs STUN, NAT classification, and P2P diagnostic suite |
| `pymesh topology` | None | Displays visual tree graph of network topology |
| `pymesh ping` | `<node_or_ip>` | Pings target node across mesh network |
| `pymesh ssh` | `<node_or_ip>` | Opens SSH connection to target node's mesh IP |
| `pymesh route add` | `<subnet> --via <node>` | Configures subnet router gateway |
| `pymesh key` | None | Displays public keys (Ed25519 & WireGuard X25519) |
| `pymesh identity` | None | Displays cryptographic node identity details |

---

## Controller REST API Reference

| Endpoint | Method | Request Payload | Description |
| :--- | :--- | :--- | :--- |
| `/net/login` | `GET / POST` | Form: `passkey` | Web Admin passkey authentication page |
| `/net/dashboard` | `GET` | Session Cookie | Cisco Packet Tracer interactive Web Admin dashboard |
| `/api/v1/auth/join` | `POST` | Query: `description` | Generates a new node join token |
| `/api/v1/nodes/register` | `POST` | `NodeRegistrationRequest` | Registers a node and allocates CGNAT IP |
| `/api/v1/nodes` | `GET` | None | Lists all registered mesh nodes |
| `/api/v1/nodes/{id}` | `GET` | Path: `id` | Fetches detailed node record |
| `/api/v1/network/config` | `GET` | Query: `node_id` | Generates active WireGuard peer configuration |
| `/api/v1/nodes/{id}/heartbeat`| `POST` | `HeartbeatRequest` | Updates node online status, NAT type, and endpoints |
| `/api/v1/acl` | `GET / PUT`| `ACLRuleModel` | Manages network access control rules |
| `/api/v1/routes` | `GET / POST / DELETE`| `SubnetRouteModel` | Manages advertised subnet routes |

---

## Testing & Verification

Run the automated test suite using `pytest`:

```bash
PYTHONPATH=. .venv/bin/pytest -v tests/
```

---

## Developer & License

- **Developer**: **MrHat** ([GitHub Profile](https://github.com/mrr-hatt/))
- **Repository**: [https://github.com/mrr-hatt/pymesh](https://github.com/mrr-hatt/pymesh)
- **License**: MIT License. See [LICENSE](LICENSE) for details.
