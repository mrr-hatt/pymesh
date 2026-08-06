"""
PyMesh Network Interface Web Console & Passkey Authentication Engine.
1:1 Authentic Cisco Desktop Interface Aesthetics.
"""

import secrets
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from pymesh.storage.database import DatabaseManager

logger = logging.getLogger("pymesh.web")

ADMIN_PASSKEY = secrets.token_urlsafe(12)
ACTIVE_SESSIONS = set()

router = APIRouter(prefix="/net")
db_manager = DatabaseManager()


def print_startup_banner():
    banner = f"""
====================================================================
 [PyMesh Network Interface] Dashboard Console Ready
 [PyMesh Network Interface] Dashboard URL: http://0.0.0.0:8000/net/login
 [PyMesh Network Interface] Passkey:       {ADMIN_PASSKEY}
====================================================================
"""
    print(banner)
    logger.info(f"PyMesh Admin Passkey generated: {ADMIN_PASSKEY}")


async def get_db():
    async for session in db_manager.get_session():
        yield session


def is_authenticated(request: Request) -> bool:
    token = request.cookies.get("pymesh_session")
    return token in ACTIVE_SESSIONS if token else False


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if is_authenticated(request):
        return RedirectResponse(url="/net/dashboard", status_code=status.HTTP_302_FOUND)

    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Network Interface | Login Console</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }}
        body {{
            background: #004b7a;
            height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #333;
        }}
        .login-card {{
            background: #ffffff;
            border: 1px solid #b0bec5;
            border-radius: 6px;
            padding: 30px 40px;
            width: 100%;
            max-width: 420px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.3);
        }}
        .brand {{
            text-align: center;
            margin-bottom: 25px;
            border-bottom: 2px solid #005B94;
            padding-bottom: 15px;
        }}
        .brand h1 {{
            font-size: 24px;
            font-weight: 700;
            color: #005B94;
        }}
        .brand p {{
            font-size: 12px;
            color: #555;
            margin-top: 4px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .form-group {{
            margin-bottom: 20px;
        }}
        label {{
            display: block;
            font-size: 12px;
            font-weight: bold;
            color: #444;
            margin-bottom: 6px;
        }}
        input[type="password"] {{
            width: 100%;
            padding: 10px;
            background: #f8f9fa;
            border: 1px solid #cccccc;
            border-radius: 4px;
            color: #005B94;
            font-size: 15px;
            outline: none;
            text-align: center;
            letter-spacing: 2px;
            font-family: monospace;
        }}
        input[type="password"]:focus {{
            border-color: #005B94;
            background: #fff;
        }}
        button {{
            width: 100%;
            padding: 10px;
            background: #005B94;
            color: white;
            border: none;
            border-radius: 4px;
            font-size: 14px;
            font-weight: bold;
            cursor: pointer;
        }}
        button:hover {{
            background: #004b7a;
        }}
        .hint {{
            font-size: 11px;
            color: #666;
            text-align: center;
            margin-top: 18px;
            line-height: 1.4;
        }}
    </style>
</head>
<body>
    <div class="login-card">
        <div class="brand">
            <h1>Network Interface</h1>
            <p>Admin Authorization Console</p>
        </div>
        <form action="/net/login" method="POST">
            <div class="form-group">
                <label for="passkey">CONTROLLER STARTUP PASSKEY</label>
                <input type="password" id="passkey" name="passkey" placeholder="Enter passkey" required autofocus>
            </div>
            <button type="submit">Authenticate Session</button>
        </form>
        <div class="hint">
            The passkey is generated dynamically on controller startup and printed in the terminal console output.
        </div>
    </div>
</body>
</html>
"""
    return HTMLResponse(content=html_content)


@router.post("/login")
async def process_login(passkey: str = Form(...)):
    if passkey == ADMIN_PASSKEY:
        session_token = secrets.token_urlsafe(24)
        ACTIVE_SESSIONS.add(session_token)
        response = RedirectResponse(url="/net/dashboard", status_code=status.HTTP_302_FOUND)
        response.set_cookie(key="pymesh_session", value=session_token, httponly=True)
        return response
    else:
        return HTMLResponse(
            content="""
            <script>
                alert('Invalid Startup Passkey');
                window.location.href = '/net/login';
            </script>
            """,
            status_code=401,
        )


@router.get("/", response_class=RedirectResponse)
@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: AsyncSession = Depends(get_db)):
    if not is_authenticated(request):
        return RedirectResponse(url="/net/login", status_code=status.HTTP_302_FOUND)

    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Network Interface</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: Arial, Helvetica, sans-serif; font-size: 12px; }
        body { background: #e0e0e0; color: #000; height: 100vh; overflow: hidden; display: flex; flex-direction: column; }
        
        /* Cisco Navy Top Header */
        .cisco-header {
            background: #005B94;
            color: #ffffff;
            height: 32px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 10px;
            font-weight: bold;
        }
        .header-title { font-size: 13px; letter-spacing: 0.5px; }

        /* Menu Bar */
        .menu-bar {
            background: #f0f0f0;
            border-bottom: 1px solid #c0c0c0;
            display: flex;
            padding: 2px 5px;
            gap: 15px;
        }
        .menu-item { cursor: pointer; padding: 2px 6px; color: #222; }
        .menu-item:hover { background: #3399ff; color: #fff; }

        /* Action Toolbar */
        .action-toolbar {
            background: #e8e8e8;
            border-bottom: 1px solid #b0b0b0;
            display: flex;
            align-items: center;
            padding: 4px 8px;
            gap: 6px;
        }
        .tool-btn {
            background: #f4f4f4;
            border: 1px solid #adadad;
            border-radius: 2px;
            padding: 3px 8px;
            cursor: pointer;
            font-size: 11px;
            color: #333;
        }
        .tool-btn:hover { background: #e2e2e2; border-color: #777; }
        .tool-separator { width: 1px; height: 18px; background: #b0b0b0; margin: 0 4px; }

        /* Workspace Mode Bar */
        .workspace-bar {
            background: #d8d8d8;
            border-bottom: 1px solid #b0b0b0;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 2px 10px;
        }
        .mode-tabs { display: flex; gap: 2px; }
        .mode-tab {
            background: #c8c8c8;
            border: 1px solid #999;
            padding: 3px 12px;
            cursor: pointer;
            font-weight: bold;
        }
        .mode-tab.active { background: #ffffff; border-bottom: 1px solid #ffffff; }

        /* Main Workspace split */
        .main-container { display: flex; flex: 1; height: calc(100vh - 200px); }

        /* Left/Center Light Schematic Canvas */
        .canvas-container {
            flex: 1;
            position: relative;
            background: #ffffff;
            background-image: radial-gradient(#d1d5db 1px, transparent 1px);
            background-size: 20px 20px;
            overflow: auto;
        }
        svg#packet-canvas { width: 100%; height: 100%; position: absolute; top: 0; left: 0; }

        /* Right Inspector & Properties Drawer */
        .inspector-drawer {
            width: 320px;
            background: #f4f4f4;
            border-left: 1px solid #b0b0b0;
            display: flex;
            flex-direction: column;
            padding: 10px;
            gap: 10px;
            overflow-y: auto;
        }
        .box-card {
            background: #ffffff;
            border: 1px solid #cccccc;
            border-radius: 3px;
            padding: 10px;
        }
        .box-title { font-weight: bold; color: #005B94; border-bottom: 1px solid #e0e0e0; padding-bottom: 4px; margin-bottom: 8px; }
        
        /* Bottom Area Split (Device Carousel & PDU Event List) */
        .bottom-container {
            height: 140px;
            background: #e8e8e8;
            border-top: 2px solid #b0b0b0;
            display: flex;
        }

        .device-carousel {
            width: 55%;
            border-right: 1px solid #b0b0b0;
            display: flex;
            flex-direction: column;
        }
        .carousel-cats {
            background: #d0d0d0;
            border-bottom: 1px solid #b0b0b0;
            display: flex;
            gap: 2px;
            padding: 2px 4px;
        }
        .cat-btn {
            background: #e0e0e0;
            border: 1px solid #a0a0a0;
            padding: 2px 8px;
            cursor: pointer;
            font-size: 11px;
        }
        .cat-btn.active { background: #ffffff; font-weight: bold; }
        .carousel-items {
            flex: 1;
            padding: 8px;
            display: flex;
            gap: 15px;
            align-items: center;
            overflow-x: auto;
            background: #f8f8f8;
        }
        .device-item {
            display: flex;
            flex-direction: column;
            align-items: center;
            cursor: pointer;
            padding: 4px 8px;
            border: 1px solid transparent;
        }
        .device-item:hover { border: 1px solid #005B94; background: #e8f4fc; }

        .pdu-simulator {
            flex: 1;
            display: flex;
            flex-direction: column;
            background: #ffffff;
        }
        .pdu-header {
            background: #d0d0d0;
            border-bottom: 1px solid #b0b0b0;
            display: flex;
            justify-content: space-between;
            padding: 3px 8px;
            font-weight: bold;
        }
        .pdu-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 11px;
        }
        .pdu-table th, .pdu-table td {
            border: 1px solid #d0d0d0;
            padding: 3px 6px;
            text-align: left;
        }
        .pdu-table th { background: #e8e8e8; }

        /* Modal Dialog */
        .modal-overlay {
            display: none;
            position: fixed;
            top: 0; left: 0; width: 100vw; height: 100vh;
            background: rgba(0,0,0,0.4);
            align-items: center;
            justify-content: center;
            z-index: 1000;
        }
        .modal-body {
            background: #ffffff;
            border: 2px solid #005B94;
            width: 440px;
            padding: 20px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.3);
        }
        .modal-header { font-size: 14px; font-weight: bold; color: #005B94; margin-bottom: 12px; }
        input[type="text"] { width: 100%; padding: 6px; border: 1px solid #ccc; margin: 4px 0 12px 0; }
        .btn-group { display: flex; justify-content: flex-end; gap: 8px; }
    </style>
</head>
<body>
    <!-- Top Cisco Navy Header -->
    <div class="cisco-header">
        <div class="header-title">Network Interface</div>
        <div>Topology Mode: Realtime Sync</div>
    </div>

    <!-- Menu Bar -->
    <div class="menu-bar">
        <div class="menu-item">File</div>
        <div class="menu-item">Edit</div>
        <div class="menu-item">Options</div>
        <div class="menu-item">View</div>
        <div class="menu-item">Tools</div>
        <div class="menu-item">Extensions</div>
        <div class="menu-item">Window</div>
        <div class="menu-item">Help</div>
    </div>

    <!-- Action Toolbar -->
    <div class="action-toolbar">
        <button class="tool-btn" onclick="fetchNetworkData()">Refresh</button>
        <button class="tool-btn" onclick="openSubnetModal()">Subnet Configuration</button>
        <div class="tool-separator"></div>
        <button class="tool-btn" onclick="setTool('select')">Select</button>
        <button class="tool-btn" onclick="setTool('inspect')">Inspect</button>
        <button class="tool-btn" onclick="setTool('delete')">Delete</button>
        <div class="tool-separator"></div>
        <button class="tool-btn" onclick="firePacketSimulation()">Fire Simulation PDU</button>
    </div>

    <!-- Workspace Bar -->
    <div class="workspace-bar">
        <div class="mode-tabs">
            <div class="mode-tab active">Logical</div>
            <div class="mode-tab">Physical</div>
        </div>
        <div>Location: <b>Root</b> | Simulation Clock: <span id="clock-display">02:45:00</span></div>
    </div>

    <!-- Main Workspace -->
    <div class="main-container">
        <!-- Light Schematic Canvas -->
        <div class="canvas-container">
            <svg id="packet-canvas">
                <!-- Schematic SVG items rendered via JS -->
            </svg>
        </div>

        <!-- Right Inspector Drawer -->
        <div class="inspector-drawer" id="inspector">
            <div class="box-card">
                <div class="box-title">Network Overview</div>
                <div style="margin-bottom:6px;">IPv4 Subnet: <b id="sub-v4">100.64.0.0/10</b></div>
                <div>IPv6 Subnet: <b id="sub-v6">fd00:7079:6d65::/48</b></div>
            </div>
            <div class="box-card" id="node-details">
                <div class="box-title">Device Inspector</div>
                <p style="color:#666;">Click any device on the schematic canvas to inspect interface details and reprogram parameters.</p>
            </div>
        </div>
    </div>

    <!-- Bottom Container (Carousel & PDU Event List) -->
    <div class="bottom-container">
        <div class="device-carousel">
            <div class="carousel-cats">
                <div class="cat-btn active">Routers</div>
                <div class="cat-btn">Switches</div>
                <div class="cat-btn">End Devices</div>
                <div class="cat-btn">Connections</div>
            </div>
            <div class="carousel-items">
                <div class="device-item">
                    <div style="font-weight:bold; color:#005B94;">2911</div>
                    <div>ISR Router</div>
                </div>
                <div class="device-item">
                    <div style="font-weight:bold; color:#005B94;">2960</div>
                    <div>Switch</div>
                </div>
                <div class="device-item">
                    <div style="font-weight:bold; color:#005B94;">PC-PT</div>
                    <div>Workstation</div>
                </div>
                <div class="device-item">
                    <div style="font-weight:bold; color:#005B94;">Server-PT</div>
                    <div>Linux Server</div>
                </div>
            </div>
        </div>

        <div class="pdu-simulator">
            <div class="pdu-header">
                <div>Simulation Event List</div>
                <div>Mode: Realtime</div>
            </div>
            <table class="pdu-table">
                <thead>
                    <tr>
                        <th>Fire</th>
                        <th>Status</th>
                        <th>Source</th>
                        <th>Destination</th>
                        <th>Type</th>
                        <th>Time(sec)</th>
                    </tr>
                </thead>
                <tbody id="pdu-list">
                    <tr>
                        <td>Success</td>
                        <td>Active</td>
                        <td>client-pc</td>
                        <td>vps-de</td>
                        <td>ICMP/WG</td>
                        <td>0.002</td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>

    <!-- Subnet Configuration Modal -->
    <div class="modal-overlay" id="subnet-modal">
        <div class="modal-body">
            <div class="modal-header">Reallocate Network Subnet IP</div>
            <p style="margin-bottom:10px; color:#555;">Changing the network CIDR will validate the prefix and automatically instruct all nodes to update their local TUN interface and WireGuard allowed IPs.</p>
            
            <label>New IPv4 Subnet CIDR Prefix</label>
            <input type="text" id="input-v4" value="100.64.0.0/10">

            <label>New IPv6 Subnet CIDR Prefix</label>
            <input type="text" id="input-v6" value="fd00:7079:6d65::/48">

            <div id="sub-error" style="color:red; font-weight:bold; margin-bottom:10px; display:none;"></div>

            <div class="btn-group">
                <button class="tool-btn" onclick="closeSubnetModal()">Cancel</button>
                <button class="tool-btn" style="background:#005B94; color:#fff;" onclick="submitSubnetChange()">Apply Subnet Reallocation</button>
            </div>
        </div>
    </div>

    <script>
        let nodesData = [];

        async function fetchNetworkData() {
            try {
                const res = await fetch('/api/v1/nodes');
                if (res.ok) {
                    nodesData = await res.json();
                    renderCanvas();
                }
            } catch (e) {
                console.error(e);
            }
        }

        function renderCanvas() {
            const svg = document.getElementById('packet-canvas');
            svg.innerHTML = '';

            const width = svg.clientWidth || 800;
            const height = svg.clientHeight || 500;
            const cx = width / 2;
            const cy = height / 2;
            const radius = 180;

            // Render Central Router
            const centerG = document.createElementNS("http://www.w3.org/2000/svg", "g");
            centerG.innerHTML = `
                <rect x="${cx - 30}" y="${cy - 20}" width="60" height="40" fill="#005B94" rx="4" />
                <text x="${cx}" y="${cy + 5}" fill="#ffffff" font-size="11" font-weight="bold" text-anchor="middle">Controller</text>
                <text x="${cx}" y="${cy + 35}" fill="#333" font-size="10" font-weight="bold" text-anchor="middle">100.64.0.1</text>
            `;
            svg.appendChild(centerG);

            nodesData.forEach((node, i) => {
                const angle = (i / nodesData.length) * 2 * Math.PI;
                const nx = cx + radius * Math.cos(angle);
                const ny = cy + radius * Math.sin(angle);

                // Connection line
                const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
                line.setAttribute("x1", cx);
                line.setAttribute("y1", cy);
                line.setAttribute("x2", nx);
                line.setAttribute("y2", ny);
                line.setAttribute("stroke", "#555555");
                line.setAttribute("stroke-width", "2");
                svg.appendChild(line);

                // Green Link Status Triangles (Cisco Style)
                const tri1 = document.createElementNS("http://www.w3.org/2000/svg", "polygon");
                const m1x = cx + 40 * Math.cos(angle);
                const m1y = cy + 40 * Math.sin(angle);
                tri1.setAttribute("points", `${m1x},${m1y-5} ${m1x+6},${m1y+5} ${m1x-6},${m1y+5}`);
                tri1.setAttribute("fill", "#00c853");
                svg.appendChild(tri1);

                // Node Box
                const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
                g.onclick = () => inspectNode(node);
                g.style.cursor = "pointer";

                const strokeColor = node.online ? "#00c853" : "#d50000";
                g.innerHTML = `
                    <rect x="${nx - 35}" y="${ny - 20}" width="70" height="40" fill="#ffffff" stroke="${strokeColor}" stroke-width="2" rx="3" />
                    <text x="${nx}" y="${ny + 2}" fill="#000000" font-size="10" font-weight="bold" text-anchor="middle">${node.hostname}</text>
                    <text x="${nx}" y="${ny + 35}" fill="#444444" font-size="10" text-anchor="middle">${node.mesh_ipv4}</text>
                `;
                svg.appendChild(g);
            });
        }

        function inspectNode(node) {
            const container = document.getElementById('node-details');
            container.innerHTML = `
                <div class="box-title">Device: ${node.hostname}</div>
                <div style="margin-bottom:4px;"><b>Node ID:</b> ${node.id.substring(0, 10)}...</div>
                <div style="margin-bottom:4px;"><b>Mesh IPv4:</b> ${node.mesh_ipv4}</div>
                <div style="margin-bottom:4px;"><b>Mesh IPv6:</b> ${node.mesh_ipv6}</div>
                <div style="margin-bottom:4px;"><b>Status:</b> ${node.online ? 'ONLINE' : 'OFFLINE'}</div>
                <div style="margin-bottom:4px;"><b>OS:</b> ${node.os}</div>
                <div style="margin-bottom:4px;"><b>WG Key:</b> ${node.wireguard_public_key.substring(0, 10)}...</div>
            `;
        }

        function openSubnetModal() {
            document.getElementById('subnet-modal').style.display = 'flex';
        }
        function closeSubnetModal() {
            document.getElementById('subnet-modal').style.display = 'none';
        }

        async function submitSubnetChange() {
            const v4 = document.getElementById('input-v4').value;
            const v6 = document.getElementById('input-v6').value;
            const err = document.getElementById('sub-error');
            err.style.display = 'none';

            try {
                const res = await fetch(`/api/v1/network/subnet?ipv4_prefix=${encodeURIComponent(v4)}&ipv6_prefix=${encodeURIComponent(v6)}`, {
                    method: 'PUT'
                });
                if (res.ok) {
                    const data = await res.json();
                    document.getElementById('sub-v4').innerText = v4;
                    document.getElementById('sub-v6').innerText = v6;
                    closeSubnetModal();
                    alert(`Subnet updated! ${data.nodes_reallocated} nodes automatically re-allocated.`);
                    fetchNetworkData();
                } else {
                    const errData = await res.json();
                    err.innerText = errData.detail || "Invalid CIDR notation";
                    err.style.display = 'block';
                }
            } catch (e) {
                err.innerText = "Connection error";
                err.style.display = 'block';
            }
        }

        function setTool(tool) {
            console.log("Active Tool:", tool);
        }

        function firePacketSimulation() {
            const list = document.getElementById('pdu-list');
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>Success</td>
                <td>Completed</td>
                <td>client-pc</td>
                <td>vps-de</td>
                <td>ICMP</td>
                <td>${(Math.random() * 0.01).toFixed(3)}</td>
            `;
            list.appendChild(row);
        }

        window.onload = fetchNetworkData;
        window.onresize = renderCanvas;
    </script>
</body>
</html>
"""
    return HTMLResponse(content=html_content)
