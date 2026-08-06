# PyMesh - Zero-Trust Private Mesh Networking

PyMesh is a zero-trust, private encrypted mesh networking platform that connects PCs, VPS instances, servers, containers, and entire remote subnets across NATs and firewalls.

Created by **MrHat** ([GitHub Profile](https://github.com/mrr-hatt/)). Official repository: [https://github.com/mrr-hatt/pymesh](https://github.com/mrr-hatt/pymesh).

PyMesh pairs WireGuard for kernel data-plane packet encryption with Python for control-plane coordination, dynamic NAT discovery, zero-decryption UDP relaying, Magic DNS, local port forwarding, access control (ACL) enforcement, dynamic valid subnet re-allocation, and an authentic desktop Network Interface web console.

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
5. [Network Interface Web Console](#network-interface-web-console)
6. [Advanced Features](#advanced-features)
   - [Dynamic Subnet Re-allocation & Auto Node Sync](#dynamic-subnet-re-allocation--auto-node-sync)
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
                         | Subnet Re-allocator  |
                         | ACL & Subnet Routes  |
                         | Network Interface    |
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

- **Network Interface Web Console**: Authentic desktop schematic canvas matching Cisco Packet Tracer layout (Cisco navy `#005B94` header, menu bars, action toolbars, green link status lights, device carousel, Realtime PDU simulation logs).
- **Dynamic Subnet Re-allocation**: Change the network IPv4/IPv6 CIDR (e.g. `10.200.0.0/16`) on the fly. The server validates CIDR syntax and automatically instructs all nodes to re-address their local TUN interfaces and update WireGuard peer allowed IPs.
- **Dynamic Startup Passkey**: Generates a new secure admin passkey on every controller restart, outputting the key directly to the server terminal output.
- **Cryptographic Node Identity**: Every node generates an Ed25519 identity keypair and an X25519 WireGuard keypair upon initialization.
- **NAT Traversal & UDP Hole Punching**: Integrated STUN client (RFC 5389) discovers public reflexive endpoints and initiates simultaneous UDP hole punching bursts.
- **Zero-Decryption UDP Relay**: Encrypted relay servers (`pymesh-relay`) forward framed WireGuard traffic when firewalls prevent direct P2P.
- **Magic DNS**: Local UDP DNS server resolves hostnames ending in `.mesh` (e.g. `vps-de.mesh`) directly to 100.64.0.x CGNAT addresses.
- **Local Port Forwarding**: Expose remote services running on any node directly on `http://localhost:port`.

---

## Deployment Tutorial

### Step 1: Start the Controller Server

```bash
python -m controller.app
```

Upon startup, the controller displays the dynamic admin passkey in the console output:

```text
====================================================================
 [PyMesh Network Interface] Dashboard Console Ready
 [PyMesh Network Interface] Dashboard URL: http://0.0.0.0:8000/net/login
 [PyMesh Network Interface] Passkey:       aB3xK9mP2qR5...
====================================================================
```

---

## Network Interface Web Console

Open **`http://<controller>:8000/net/login`** in your browser to access the web console.

1. **Authentication**: Enter the startup passkey printed in the controller terminal output.
2. **Schematic Topology Canvas**: View all connected mesh nodes, IP allocations, active WireGuard links, and green triangle link status lights.
3. **Subnet Reallocation**: Click **Subnet Configuration** on the action toolbar to edit the network CIDR prefix. Validates CIDR syntax and auto-updates all connected nodes.
4. **Device Inspector**: Click any device node on the canvas to inspect interface metrics, OS, WireGuard keys, and IP addresses.
5. **Realtime PDU Event Log**: View ICMP/UDP simulation packet events in the bottom PDU event list table.

---

## Advanced Features

### Dynamic Subnet Re-allocation & Auto Node Sync

Change the global mesh IP pool dynamically:

```bash
curl -X PUT "http://localhost:8000/api/v1/network/subnet?ipv4_prefix=10.200.0.0/16"
```

Nodes receive the new subnet prefix on their periodic sync, automatically re-assigning their local `pymesh0` TUN interface IP and syncing WireGuard peers without manual intervention.

### Local Port Forwarding & Proxy

```bash
# Forward local http://localhost:8000 -> port 8000 on node vps-de
pymesh forward vps-de 8000
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
| `/net/login` | `GET / POST` | Form: `passkey` | Web Admin passkey authentication page |
| `/net/dashboard` | `GET` | Session Cookie | Network Interface web console |
| `/api/v1/network/subnet` | `PUT` | Query: `ipv4_prefix`, `ipv6_prefix` | Validates & re-allocates network CIDR across all nodes |
| `/api/v1/nodes` | `GET` | None | Lists all registered mesh nodes |
| `/api/v1/network/config` | `GET` | Query: `node_id` | Generates active WireGuard peer configuration |

---

## Developer & License

- **Developer**: **MrHat** ([GitHub Profile](https://github.com/mrr-hatt/))
- **Repository**: [https://github.com/mrr-hatt/pymesh](https://github.com/mrr-hatt/pymesh)
- **License**: MIT License. See [LICENSE](LICENSE) for details.
