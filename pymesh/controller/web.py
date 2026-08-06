"""
PyMesh Network Interface Web Console & Passkey Authentication Engine.
Authentic Cisco Desktop Layout with Real Network Node SVGs, Interactive Subnet Config, and PDU Animation.
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
            height: 36px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 14px;
            font-weight: bold;
        }
        .header-title { font-size: 14px; letter-spacing: 0.5px; }

        /* Action Toolbar */
        .action-toolbar {
            background: #e8e8e8;
            border-bottom: 1px solid #b0b0b0;
            display: flex;
            align-items: center;
            padding: 6px 12px;
            gap: 8px;
        }
        .tool-btn {
            background: #ffffff;
            border: 1px solid #adadad;
            border-radius: 3px;
            padding: 4px 10px;
            cursor: pointer;
            font-size: 11px;
            font-weight: bold;
            color: #333;
            display: flex;
            align-items: center;
            gap: 4px;
        }
        .tool-btn:hover { background: #e2e2e2; border-color: #005B94; }
        .tool-btn.active { background: #005B94; color: #ffffff; border-color: #004b7a; }
        .tool-separator { width: 1px; height: 20px; background: #b0b0b0; margin: 0 4px; }

        /* Main Workspace split */
        .main-container { display: flex; flex: 1; height: calc(100vh - 190px); }

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

        /* Right Inspector Drawer */
        .inspector-drawer {
            width: 320px;
            background: #f4f4f4;
            border-left: 1px solid #b0b0b0;
            display: flex;
            flex-direction: column;
            padding: 12px;
            gap: 12px;
            overflow-y: auto;
        }
        .box-card {
            background: #ffffff;
            border: 1px solid #cccccc;
            border-radius: 4px;
            padding: 12px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }
        .box-title { font-weight: bold; color: #005B94; border-bottom: 1px solid #e0e0e0; padding-bottom: 5px; margin-bottom: 10px; }
        .info-row { display: flex; justify-content: space-between; margin-bottom: 6px; font-size: 11px; }
        .info-label { color: #555; font-weight: bold; }
        .info-val { color: #111; word-break: break-all; }

        /* Bottom Area Split (Device Carousel & PDU Event List) */
        .bottom-container {
            height: 140px;
            background: #e8e8e8;
            border-top: 2px solid #b0b0b0;
            display: flex;
        }

        .device-carousel {
            width: 50%;
            border-right: 1px solid #b0b0b0;
            display: flex;
            flex-direction: column;
        }
        .carousel-cats {
            background: #d0d0d0;
            border-bottom: 1px solid #b0b0b0;
            display: flex;
            gap: 2px;
            padding: 3px 6px;
        }
        .cat-btn {
            background: #e0e0e0;
            border: 1px solid #a0a0a0;
            padding: 3px 10px;
            cursor: pointer;
            font-size: 11px;
            border-radius: 2px;
        }
        .cat-btn.active { background: #ffffff; font-weight: bold; border-color: #005B94; color: #005B94; }
        .carousel-items {
            flex: 1;
            padding: 10px;
            display: flex;
            gap: 20px;
            align-items: center;
            overflow-x: auto;
            background: #f8f8f8;
        }
        .device-item {
            display: flex;
            flex-direction: column;
            align-items: center;
            cursor: pointer;
            padding: 6px 10px;
            border: 1px solid transparent;
            border-radius: 4px;
            min-width: 80px;
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
            padding: 4px 10px;
            font-weight: bold;
        }
        .pdu-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 11px;
        }
        .pdu-table th, .pdu-table td {
            border: 1px solid #d0d0d0;
            padding: 4px 8px;
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
            border-radius: 4px;
            width: 440px;
            padding: 20px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.3);
        }
        .modal-header { font-size: 15px; font-weight: bold; color: #005B94; margin-bottom: 12px; }
        input[type="text"] { width: 100%; padding: 8px; border: 1px solid #ccc; border-radius: 3px; margin: 4px 0 12px 0; }
        .btn-group { display: flex; justify-content: flex-end; gap: 8px; }

        /* SVG Animated Packet */
        @keyframes pduPulse {
            0% { r: 5px; fill: #005B94; }
            50% { r: 9px; fill: #00c853; }
            100% { r: 5px; fill: #005B94; }
        }
        .pdu-dot { animation: pduPulse 1s infinite; }
    </style>
</head>
<body>
    <!-- Top Cisco Navy Header -->
    <div class="cisco-header">
        <div class="header-title">Network Interface</div>
        <div>
            Status: <span style="color:#00e676; font-weight:bold;">ONLINE</span>
            <a href="/net/login" style="color:#ffffff; margin-left:15px; text-decoration:underline;">Logout</a>
        </div>
    </div>

    <!-- Action Toolbar -->
    <div class="action-toolbar">
        <button class="tool-btn" onclick="fetchNetworkData()">Refresh Topology</button>
        <button class="tool-btn" onclick="openSubnetModal()">Subnet Configuration</button>
        <div class="tool-separator"></div>
        <button class="tool-btn active" id="btn-select" onclick="setTool('select')">Select Tool</button>
        <button class="tool-btn" id="btn-inspect" onclick="setTool('inspect')">Inspect Device</button>
        <button class="tool-btn" id="btn-delete" onclick="setTool('delete')">Delete Device</button>
        <div class="tool-separator"></div>
        <button class="tool-btn" style="background:#005B94; color:#fff;" onclick="firePacketSimulation()">Fire Simulation PDU</button>
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
        <div class="inspector-drawer">
            <div class="box-card">
                <div class="box-title">Subnet Overview</div>
                <div class="info-row"><span class="info-label">IPv4 Prefix:</span><span class="info-val" id="sub-v4">100.64.0.0/10</span></div>
                <div class="info-row"><span class="info-label">IPv6 Prefix:</span><span class="info-val" id="sub-v6">fd00:7079:6d65::/48</span></div>
            </div>

            <div class="box-card" id="node-details">
                <div class="box-title">Device Inspector</div>
                <p style="color:#666;">Click any device on the schematic canvas using the <b>Inspect Tool</b> to view parameters and interface statistics.</p>
            </div>
        </div>
    </div>

    <!-- Bottom Container (Carousel & PDU Event List) -->
    <div class="bottom-container">
        <div class="device-carousel">
            <div class="carousel-cats">
                <div class="cat-btn active" onclick="switchCategory('routers', this)">Routers</div>
                <div class="cat-btn" onclick="switchCategory('switches', this)">Switches</div>
                <div class="cat-btn" onclick="switchCategory('enddevices', this)">End Devices</div>
                <div class="cat-btn" onclick="switchCategory('connections', this)">Connections</div>
            </div>
            <div class="carousel-items" id="carousel-content">
                <!-- Items dynamically populated -->
            </div>
        </div>

        <div class="pdu-simulator">
            <div class="pdu-header">
                <div>Simulation Event List</div>
                <div>Status: Realtime Active</div>
            </div>
            <div style="overflow-y:auto; flex:1;">
                <table class="pdu-table">
                    <thead>
                        <tr>
                            <th>Status</th>
                            <th>Source</th>
                            <th>Destination</th>
                            <th>Protocol</th>
                            <th>Time(sec)</th>
                        </tr>
                    </thead>
                    <tbody id="pdu-list">
                        <tr>
                            <td style="color:#00c853; font-weight:bold;">Success</td>
                            <td>client-pc</td>
                            <td>SV1</td>
                            <td>ICMP / WG</td>
                            <td>0.004</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <!-- Subnet Configuration Modal -->
    <div class="modal-overlay" id="subnet-modal">
        <div class="modal-body">
            <div class="modal-header">Reallocate Network Subnet IP</div>
            <p style="margin-bottom:12px; color:#555;">Changing the network CIDR will validate the prefix and automatically instruct all nodes to update their local TUN interface and WireGuard allowed IPs.</p>
            
            <label style="font-weight:bold;">New IPv4 Subnet CIDR Prefix</label>
            <input type="text" id="input-v4" value="100.64.0.0/10">

            <label style="font-weight:bold;">New IPv6 Subnet CIDR Prefix</label>
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
        let activeTool = 'select';
        let selectedNode = null;

        // Cisco Device SVG Templates
        const SVG_ICONS = {
            router: `
                <g>
                    <ellipse cx="0" cy="0" rx="24" ry="14" fill="#005B94" stroke="#003d63" stroke-width="2"/>
                    <path d="M-12,0 L12,0 M0,-7 L0,7 M-8,-4 L8,4 M-8,4 L8,-4" stroke="#ffffff" stroke-width="2" stroke-linecap="round"/>
                </g>`,
            switch: `
                <g>
                    <rect x="-24" y="-12" width="48" height="24" rx="3" fill="#005B94" stroke="#003d63" stroke-width="2"/>
                    <path d="M-14,-4 L14,-4 M-14,4 L14,4 M-6,-8 L-14,-4 L-6,0 M6,0 L14,4 L6,8" stroke="#ffffff" stroke-width="1.5" stroke-linecap="round" fill="none"/>
                </g>`,
            server: `
                <g>
                    <rect x="-22" y="-16" width="44" height="32" rx="4" fill="#374151" stroke="#1f2937" stroke-width="2"/>
                    <rect x="-18" y="-12" width="36" height="8" fill="#111827"/>
                    <rect x="-18" y="-1" width="36" height="8" fill="#111827"/>
                    <rect x="-18" y="10" width="36" height="4" fill="#111827"/>
                    <circle cx="12" cy="-8" r="1.5" fill="#00c853"/>
                    <circle cx="12" cy="3" r="1.5" fill="#00c853"/>
                </g>`,
            pc: `
                <g>
                    <rect x="-20" y="-18" width="40" height="26" rx="2" fill="#e5e7eb" stroke="#374151" stroke-width="2"/>
                    <rect x="-16" y="-14" width="32" height="18" fill="#1e293b"/>
                    <path d="M-6,8 L6,8 M0,8 L0,14 M-12,14 L12,14" stroke="#374151" stroke-width="2"/>
                </g>`,
            laptop: `
                <g>
                    <rect x="-16" y="-14" width="32" height="20" rx="2" fill="#374151" stroke="#111827" stroke-width="1.5"/>
                    <rect x="-13" y="-11" width="26" height="14" fill="#0f172a"/>
                    <path d="M-22,8 L22,8 L20,12 L-20,12 Z" fill="#9ca3af" stroke="#374151"/>
                </g>`
        };

        const CAROUSEL_DATA = {
            routers: [
                { name: "2911 Router", type: "router" },
                { name: "1941 Router", type: "router" },
                { name: "4331 ISR", type: "router" }
            ],
            switches: [
                { name: "2960 Switch", type: "switch" },
                { name: "3560-24PS", type: "switch" }
            ],
            enddevices: [
                { name: "PC-PT Workstation", type: "pc" },
                { name: "Laptop-PT", type: "laptop" },
                { name: "Server-PT", type: "server" }
            ],
            connections: [
                { name: "Straight-Through", type: "cable" },
                { name: "Cross-Over", type: "cable" }
            ]
        };

        function setTool(tool) {
            activeTool = tool;
            ['select', 'inspect', 'delete'].forEach(t => {
                const btn = document.getElementById('btn-' + t);
                if (btn) btn.classList.toggle('active', t === tool);
            });
        }

        function switchCategory(cat, el) {
            document.querySelectorAll('.cat-btn').forEach(b => b.classList.remove('active'));
            el.classList.add('active');
            renderCarousel(cat);
        }

        function renderCarousel(cat) {
            const container = document.getElementById('carousel-content');
            const items = CAROUSEL_DATA[cat] || [];
            container.innerHTML = items.map(item => `
                <div class="device-item" onclick="alert('Drag or add ${item.name} to topology canvas')">
                    <svg width="48" height="36" viewBox="-26 -20 52 40">
                        ${SVG_ICONS[item.type] || SVG_ICONS['pc']}
                    </svg>
                    <div style="margin-top:4px; font-weight:bold; font-size:10px;">${item.name}</div>
                </div>
            `).join('');
        }

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
            const radius = 170;

            // Render Central Controller Node
            const centerG = document.createElementNS("http://www.w3.org/2000/svg", "g");
            centerG.setAttribute("transform", `translate(${cx}, ${cy})`);
            centerG.innerHTML = `
                ${SVG_ICONS.router}
                <text x="0" y="24" fill="#005B94" font-size="11" font-weight="bold" text-anchor="middle">Controller</text>
                <text x="0" y="36" fill="#444" font-size="10" text-anchor="middle">100.64.0.1</text>
            `;
            svg.appendChild(centerG);

            // Render Registered Nodes
            nodesData.forEach((node, i) => {
                const angle = (i / nodesData.length) * 2 * Math.PI;
                const nx = cx + radius * Math.cos(angle);
                const ny = cy + radius * Math.sin(angle);

                // Cable Line
                const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
                line.setAttribute("x1", cx);
                line.setAttribute("y1", cy);
                line.setAttribute("x2", nx);
                line.setAttribute("y2", ny);
                line.setAttribute("stroke", "#4b5563");
                line.setAttribute("stroke-width", "2");
                line.setAttribute("id", `link-node-${node.id}`);
                svg.appendChild(line);

                // Green Link Status Lights
                const tri = document.createElementNS("http://www.w3.org/2000/svg", "polygon");
                const mx = cx + 35 * Math.cos(angle);
                const my = cy + 35 * Math.sin(angle);
                tri.setAttribute("points", `${mx},${my-5} ${mx+5},${my+5} ${mx-5},${my+5}`);
                tri.setAttribute("fill", "#00c853");
                svg.appendChild(tri);

                // Select Icon Type based on hostname / os
                let iconType = 'pc';
                const hName = node.hostname.toLowerCase();
                if (hName.includes('sv') || hName.includes('vps') || hName.includes('server')) iconType = 'server';
                else if (hName.includes('laptop')) iconType = 'laptop';

                const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
                g.setAttribute("transform", `translate(${nx}, ${ny})`);
                g.style.cursor = "pointer";
                g.onclick = () => handleNodeClick(node);

                const statusColor = node.online ? "#00c853" : "#d50000";
                g.innerHTML = `
                    <circle cx="0" cy="0" r="26" fill="#ffffff" stroke="${statusColor}" stroke-width="2" />
                    ${SVG_ICONS[iconType]}
                    <text x="0" y="36" fill="#111827" font-size="11" font-weight="bold" text-anchor="middle">${node.hostname}</text>
                    <text x="0" y="48" fill="#6b7280" font-size="10" text-anchor="middle">${node.mesh_ipv4}</text>
                `;
                svg.appendChild(g);
            });
        }

        async function handleNodeClick(node) {
            if (activeTool === 'inspect' || activeTool === 'select') {
                selectedNode = node;
                const container = document.getElementById('node-details');
                container.innerHTML = `
                    <div class="box-title">Device: ${node.hostname}</div>
                    <div class="info-row"><span class="info-label">Node ID:</span><span class="info-val">${node.id.substring(0, 12)}...</span></div>
                    <div class="info-row"><span class="info-label">Mesh IPv4:</span><span class="info-val">${node.mesh_ipv4}</span></div>
                    <div class="info-row"><span class="info-label">Mesh IPv6:</span><span class="info-val">${node.mesh_ipv6}</span></div>
                    <div class="info-row"><span class="info-label">Status:</span><span class="info-val" style="color:${node.online ? '#00c853':'#d50000'}; font-weight:bold;">${node.online ? 'ONLINE' : 'OFFLINE'}</span></div>
                    <div class="info-row"><span class="info-label">OS / Ver:</span><span class="info-val">${node.os} / ${node.version}</span></div>
                    <div class="info-row"><span class="info-label">NAT Type:</span><span class="info-val">${node.nat_type || 'Full Cone'}</span></div>
                    <div class="info-row"><span class="info-label">WG Key:</span><span class="info-val">${node.wireguard_public_key.substring(0, 10)}...</span></div>
                `;
            } else if (activeTool === 'delete') {
                if (confirm(`Delete node ${node.hostname} (${node.mesh_ipv4}) from controller?`)) {
                    try {
                        const res = await fetch(`/api/v1/nodes/${node.id}`, { method: 'DELETE' });
                        if (res.ok) {
                            alert(`Node ${node.hostname} deleted.`);
                            fetchNetworkData();
                        }
                    } catch (e) {
                        alert("Error deleting node");
                    }
                }
            }
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
                    alert(`Subnet updated to ${v4}! ${data.nodes_reallocated} nodes automatically re-addressed.`);
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

        function firePacketSimulation() {
            if (nodesData.length === 0) {
                alert("No connected nodes available for simulation.");
                return;
            }
            const targetNode = nodesData[Math.floor(Math.random() * nodesData.length)];
            
            // Add PDU Table Row
            const list = document.getElementById('pdu-list');
            const row = document.createElement('tr');
            row.innerHTML = `
                <td style="color:#00c853; font-weight:bold;">Success</td>
                <td>Controller</td>
                <td>${targetNode.hostname}</td>
                <td>ICMP / WG</td>
                <td>0.003</td>
            `;
            list.insertBefore(row, list.firstChild);

            // Trigger Visual SVG Animated Packet Movement
            const svg = document.getElementById('packet-canvas');
            const pduCircle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
            pduCircle.setAttribute("cx", svg.clientWidth / 2);
            pduCircle.setAttribute("cy", svg.clientHeight / 2);
            pduCircle.setAttribute("class", "pdu-dot");
            svg.appendChild(pduCircle);

            setTimeout(() => {
                try { svg.removeChild(pduCircle); } catch(e) {}
            }, 1200);
        }

        window.onload = () => {
            fetchNetworkData();
            renderCarousel('routers');
        };
        window.onresize = renderCanvas;
    </script>
</body>
</html>
"""
    return HTMLResponse(content=html_content)
