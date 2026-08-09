# PyMesh - Zero-Trust Private Mesh Networking

PyMesh is a zero-trust, private encrypted mesh networking platform connecting PCs, VPS instances, servers, containers, and remote subnets across NATs and firewalls.

Created by **MrHat** ([GitHub Profile](https://github.com/mrr-hatt/)). Official repository: [https://github.com/mrr-hatt/pymesh](https://github.com/mrr-hatt/pymesh).

PyMesh pairs native kernel WireGuard for data-plane packet encryption with Python for control-plane coordination, dynamic NAT discovery, zero-decryption UDP relaying, Magic DNS, local TCP port forwarding, access control (ACL) enforcement, dynamic valid subnet re-allocation, Custom TLD Publishing, and CR-to-CR Controller Federation.

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
   - [Custom TLD Publishing & registry.{tld} Web Page](#custom-tld-publishing--registrytld-web-page)
   - [Controller-to-Controller (CR) Federation](#controller-to-controller-cr-federation)
   - [Dynamic Subnet Re-allocation & Auto Node Sync](#dynamic-subnet-re-allocation--auto-node-sync)
   - [Local Port Forwarding & Proxy](#local-port-forwarding--proxy)
   - [Subnet Routers & Exit Nodes](#subnet-routers--exit-nodes)
   - [Magic DNS (*.mesh / *.cr)](#magic-dns-mesh--cr)
6. [System Boot Reconnection & Persistence](#system-boot-reconnection--persistence)
7. [Version Releases & Upgrade Guide](#version-releases--upgrade-guide)
8. [CLI Command Reference](#cli-command-reference)
9. [Controller REST API Reference](#controller-rest-api-reference)
10. [Testing & Verification](#testing--verification)
11. [Developer & License](#developer--license)

---

## Key Capabilities

- **Custom TLD Publishing System**: Publish browser-readable top-level domains (e.g. `.cr`, `.mesh`, `.priv`). Enforces RFC 1035 label validation (2-24 standard characters) to reject invalid strings.
- **Automatic `registry.{tld}` Web Page**: Automatically serves an HTML landing page at `http://registry.{tld}` displaying publisher details, registration rules, and domain listings.
- **100% Working System DNS for Chrome**: Embedded Magic DNS binds UDP 53/5353 and integrates system resolvers (`systemd-resolved` / `/etc/resolv.conf`) so Chrome, Firefox, `curl`, and system tools resolve `.tld` domains seamlessly.
- **CR-to-CR Controller Federation**: Mutually peer CR (Controller) servers (`pymesh cr peer <url>`) to federate node registries and TLD routing into a resilient combined bootnode network.
- **Cryptographic Node Identity**: Every node generates an Ed25519 identity keypair and an X25519 WireGuard keypair upon initialization.
- **Dynamic Subnet Re-allocation**: Change network IPv4/IPv6 CIDR (e.g. `10.200.0.0/16`) on the fly. Server validates CIDR syntax and automatically instructs all nodes to re-address local TUN interfaces.
- **Local Port Forwarding**: Expose remote services running on any node directly on `http://localhost:port` (`pymesh forward <node> <ports>`).

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

### Custom TLD Publishing & registry.{tld} Web Page

Publish a browser-compatible TLD:

```bash
pymesh tld publish cr --info "Official Primary CR Controller" --desc "Official CR Domain Registry"
```

Output:
```text
Successfully published TLD .cr!
Registry URL: http://registry.cr
```

Visiting **`http://registry.cr`** in Chrome, Firefox, or `curl` loads the interactive TLD publisher page and domain table.

---

### Controller-to-Controller (CR) Federation

Peer two CR bootnode controllers together:

```bash
pymesh cr peer http://cr2.example.com:8000
```

Check federated CR connection status:

```bash
pymesh cr status
```

---

### Dynamic Subnet Re-allocation & Auto Node Sync

Change the global mesh IP pool dynamically:

```bash
curl -X PUT "http://localhost:8000/api/v1/network/subnet?ipv4_prefix=10.200.0.0/16"
```

Nodes receive the new subnet prefix on their periodic sync, automatically re-assigning their local `pymesh0` TUN interface IP and syncing WireGuard peers without manual intervention.

---

### Local Port Forwarding & Proxy

Access remote services hosted locally on any node as if they were running on your localhost:

```bash
pymesh forward vps-de 8000
```

### Standalone PyMesh Authoritative & Upstream Recursive DNS Server

PyMesh includes a standalone UDP DNS Server (`pymesh dns server`) that resolves all custom TLD domains (`*.cr`, `*.mesh`, `registry.cr`, `registry.mesh`) and recursively forwards standard internet queries (`google.com`, `youtube.com`) to Cloudflare DNS (`1.1.1.1`).

Start the DNS server on your CR Server:

```bash
sudo pymesh dns server --port 53 --controller-url http://37.114.46.108:8000
```

#### Chrome & OS Configuration:
1. In Chrome, open **Settings** -> **Privacy and security** -> **Use Secure DNS**.
2. Choose **Custom** and enter: `http://37.114.46.108:53` (or set system IPv4 DNS to `37.114.46.108`).
3. Now `http://registry.cr:8000` and `http://<node>.cr:8000` resolve instantly in Chrome while standard websites continue working normally!

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
| `pymesh tld publish` | `<name> [--info -i] [--desc -d]` | Publishes a valid browser-readable TLD & registry page |
| `pymesh tld list` | None | Lists all published Top-Level Domains |
| `pymesh cr peer` | `<target_url>` | Initiates CR-to-CR controller federation handshake |
| `pymesh cr status` | None | Displays federated CR bootnode server connections |
| `pymesh dns server` | `[--host -h] [--port -p] [--controller-url -c]` | Starts Standalone Authoritative & Recursive DNS Server |
| `pymesh ping` | `<node_or_ip>` | Pings target node across mesh network |
| `pymesh ssh` | `<node_or_ip>` | Opens SSH connection to target node's mesh IP |

---

## Controller REST API Reference

| Endpoint | Method | Request Payload | Description |
| :--- | :--- | :--- | :--- |
| `/api/v1/tld/publish` | `POST` | Query: `name`, `description`, `publisher_info` | Publishes a browser-compatible TLD |
| `/api/v1/tld` | `GET` | None | Lists all published TLDs |
| `/registry/{tld}` | `GET` | Path: `tld_name` | Renders HTML registry landing page |
| `/api/v1/cr/peer` | `POST` | Query: `url` | Initiates CR controller federation |
| `/api/v1/cr/peers` | `GET` | None | Lists federated CR bootnode servers |
| `/api/v1/network/subnet` | `PUT` | Query: `ipv4_prefix`, `ipv6_prefix` | Validates & re-allocates network CIDR across all nodes |
| `/api/v1/nodes` | `GET` | None | Lists all registered mesh nodes |
| `/api/v1/nodes/{id}` | `DELETE` | Path: `node_id` | Deletes node registration from controller |

---

## Developer & License

- **Developer**: **MrHat** ([GitHub Profile](https://github.com/mrr-hatt/))
- **Repository**: [https://github.com/mrr-hatt/pymesh](https://github.com/mrr-hatt/pymesh)
- **License**: MIT License. See [LICENSE](LICENSE) for details.
