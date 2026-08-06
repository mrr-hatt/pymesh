# PyMesh - Zero-Trust Private Mesh Networking

PyMesh is a zero-trust, private encrypted mesh networking platform that connects PCs, VPS instances, servers, containers, and entire remote subnets across NATs and firewalls.

PyMesh pairs WireGuard for kernel data-plane packet encryption with Python for control-plane coordination, dynamic NAT discovery, zero-decryption UDP relaying, Magic DNS, local port forwarding, and access control (ACL) enforcement.

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
   - [Local Port Forwarding & Proxy](#local-port-forwarding--proxy)
   - [Subnet Routers & Exit Nodes](#subnet-routers--exit-nodes)
   - [Magic DNS (*.mesh)](#magic-dns-mesh)
   - [Access Control Lists (ACLs)](#access-control-lists-acls)
   - [NAT Traversal & UDP Relaying](#nat-traversal--udp-relaying)
6. [System Boot Reconnection & Persistence](#system-boot-reconnection--persistence)
7. [CLI Command Reference](#cli-command-reference)
8. [Controller REST API Reference](#controller-rest-api-reference)
9. [Testing & Verification](#testing--verification)
10. [License](#license)

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

- **Control Plane**: Developed in Python using FastAPI, SQLAlchemy 2.0, and Pydantic v2. Responsible for node identity registration, CGNAT IP allocation (`100.64.0.0/10` IPv4 & `fd00:7079:6d65::/48` IPv6), heartbeat tracking, ACL evaluation, and peer discovery.
- **Data Plane**: Uses native kernel WireGuard (`pyroute2`) for direct peer-to-peer packet encryption and transport. PyMesh configures WireGuard parameters without modifying underlying cryptographic transport protocols.

---

## Key Capabilities

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
git clone https://github.com/yourorg/pymesh.git
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

The controller manages node registration and peer coordination. Run it on a host reachable by all nodes.

```bash
python -m controller.app
```

By default, the server binds to `http://0.0.0.0:8000`.

To create an authentication join token (optional):

```bash
curl -X POST "http://localhost:8000/api/v1/auth/join?description=DeployToken"
```

Output:
```json
{
  "token": "YOUR_AUTH_TOKEN_HERE",
  "auth_url": "/join?token=YOUR_AUTH_TOKEN_HERE"
}
```

---

### Step 2: Start a Relay Server (Optional)

If some nodes are behind restrictive NATs, launch a relay server on a public host:

```bash
python -m relay.app 51830
```

This starts an encrypted UDP relay on port 51830.

---

### Step 3: Register Nodes

On each host that will join the mesh network, execute `pymesh join`:

#### On Node 1 (`client-pc`):
```bash
pymesh join http://controller.example.com:8000 --hostname client-pc
```

Output:
```text
Joining PyMesh controller at http://controller.example.com:8000...
Successfully joined PyMesh network!
Node ID:   8d1c5e1234567890abcdef12345678908d1c5e1234567890abcdef1234567890
Mesh IPv4: 100.64.0.2
Mesh IPv6: fd00:7079:6d65::2
```

#### On Node 2 (`vps-de`):
```bash
pymesh join http://controller.example.com:8000 --hostname vps-de
```

Output:
```text
Successfully joined PyMesh network!
Node ID:   9a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d9a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d
Mesh IPv4: 100.64.0.3
Mesh IPv6: fd00:7079:6d65::3
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

Output:
```text
PyMesh Network Diagnostics

IPv4                OK
IPv6                OK
UDP                 OK
NAT                 Full Cone NAT
Direct P2P          Possible
STUN                OK
Relay               Available

Peers
-------------------------------------------------------------
Peer Hostname        Mesh IP          Connection    Latency
-------------------------------------------------------------
vps-de               100.64.0.3       DIRECT        14 ms
database             100.64.0.4       DIRECT        8 ms
friend-server        100.64.0.5       RELAY         42 ms
```

To render the visual network topology tree:

```bash
pymesh topology
```

Output:
```text
+----------------------------- Network Topology Map -----------------------------+
| PyMesh Controller (http://controller.example.com:8000)                        |
| `-- Encrypted Private Mesh Network (100.64.0.0/10)                             |
|     |-- client-pc (100.64.0.2) - ONLINE                                       |
|     |   |-- Endpoint: 41.200.12.5:51820                                       |
|     |   `-- Groups: developers                                                |
|     |-- vps-de (100.64.0.3) - ONLINE                                          |
|     |   |-- Endpoint: 51.15.80.20:51820                                       |
|     |   `-- Groups: servers                                                   |
|     `-- database (100.64.0.4) - ONLINE                                       |
|         `-- Endpoint: 185.220.101.4:51820                                     |
+-------------------------------------------------------------------------------+
```

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

Opening `http://localhost:8000` in your local browser transparently proxies traffic over the encrypted mesh tunnel.

### Subnet Routers & Exit Nodes

Expose an internal private network (e.g. `10.10.0.0/24`) through a gateway node (`vps-de`):

```bash
pymesh route add 10.10.0.0/24 --via vps-de
```

Traffic directed to `10.10.0.0/24` across any node will automatically route through `vps-de`.

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
  },
  {
    "source": "group:developers",
    "destination": "node:database",
    "ports": [5432],
    "action": "allow"
  }
]
```

### NAT Traversal & UDP Relaying

1. **Reflexive Address Discovery**: The STUN client queries public STUN endpoints to resolve external IP and UDP port mappings.
2. **UDP Hole Punching**: Simultaneous probe bursts are transmitted to open stateful NAT mappings.
3. **Encrypted Relay Fallback**: If hole punching fails, traffic is framed using `PYRELAY` headers and routed through the relay server without decrypting WireGuard payloads.

---

## System Boot Reconnection & Persistence

Node configurations (`identity.json`) are automatically stored locally upon joining a network. Upon system reboot or service restart, the PyMesh daemon automatically reconnects to the network using its stored credentials.

To enable PyMesh to start automatically on system boot via systemd:

```bash
# Copy systemd unit configuration
sudo cp pymesh.service /etc/systemd/system/pymesh.service

# Reload systemd daemon
sudo systemctl daemon-reload

# Enable and start PyMesh daemon on boot
sudo systemctl enable --now pymesh
```

To verify background service status:
```bash
sudo systemctl status pymesh
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

Expected output:

```text
============================= test session starts ==============================
collected 13 items

tests/test_acl.py ..                                                     [ 15%]
tests/test_allocator.py .                                                [ 23%]
tests/test_cli.py ...                                                    [ 46%]
tests/test_controller.py ..                                              [ 61%]
tests/test_identity.py ...                                               [ 84%]
tests/test_relay.py .                                                    [ 92%]
tests/test_wireguard_manager.py .                                        [100%]

======================== 13 passed in 4.97s =========================
```

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
