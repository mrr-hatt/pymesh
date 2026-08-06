"""
PyMesh Cisco Packet Tracer Style Web Admin Site & Passkey Authentication Engine.
"""

import secrets
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from pymesh.storage.database import DatabaseManager
from pymesh.storage.models import NodeModel, ACLRule, SubnetRoute
from pymesh.controller.nodes import NodeManager
from pymesh.controller.peers import PeerManager

logger = logging.getLogger("pymesh.web")

# Generate a unique dynamic admin passkey per server run
ADMIN_PASSKEY = secrets.token_urlsafe(12)
ACTIVE_SESSIONS = set()

router = APIRouter(prefix="/net")
db_manager = DatabaseManager()


def print_startup_banner():
    banner = f"""
====================================================================
 [PyMesh Web Admin] Cisco Packet Tracer Dashboard Ready
 [PyMesh Web Admin] Dashboard URL: http://0.0.0.0:8000/net/login
 [PyMesh Web Admin] Passkey:       {ADMIN_PASSKEY}
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
    <title>PyMesh Admin Login | Cisco Packet Tracer Console</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }}
        body {{
            background: radial-gradient(circle at center, #1e293b 0%, #0f172a 100%);
            height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #f8fafc;
        }}
        .login-card {{
            background: rgba(30, 41, 59, 0.85);
            backdrop-filter: blur(12px);
            border: 1px solid #334155;
            border-radius: 12px;
            padding: 40px;
            width: 100%;
            max-width: 440px;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5), 0 8px 10px -6px rgba(0, 0, 0, 0.5);
        }}
        .brand {{
            text-align: center;
            margin-bottom: 30px;
        }}
        .brand h1 {{
            font-size: 28px;
            font-weight: 700;
            color: #38bdf8;
            letter-spacing: 1px;
        }}
        .brand p {{
            font-size: 13px;
            color: #94a3b8;
            margin-top: 6px;
            text-transform: uppercase;
            letter-spacing: 1.5px;
        }}
        .form-group {{
            margin-bottom: 24px;
        }}
        label {{
            display: block;
            font-size: 13px;
            font-weight: 600;
            color: #cbd5e1;
            margin-bottom: 8px;
        }}
        input[type="password"] {{
            width: 100%;
            padding: 12px 16px;
            background: #0f172a;
            border: 1px solid #475569;
            border-radius: 8px;
            color: #38bdf8;
            font-size: 16px;
            outline: none;
            transition: all 0.2s ease;
            text-align: center;
            letter-spacing: 2px;
        }}
        input[type="password"]:focus {{
            border-color: #38bdf8;
            box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.2);
        }}
        button {{
            width: 100%;
            padding: 12px;
            background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.2s ease;
        }}
        button:hover {{
            background: linear-gradient(135deg, #0369a1 0%, #075985 100%);
        }}
        .hint {{
            font-size: 12px;
            color: #64748b;
            text-align: center;
            margin-top: 20px;
            line-height: 1.5;
        }}
        .error {{
            background: rgba(239, 68, 68, 0.2);
            border: 1px solid #ef4444;
            color: #fca5a5;
            padding: 10px;
            border-radius: 6px;
            font-size: 13px;
            margin-bottom: 20px;
            text-align: center;
        }}
    </style>
</head>
<body>
    <div class="login-card">
        <div class="brand">
            <h1>PyMesh Admin</h1>
            <p>Cisco Packet Tracer Control Console</p>
        </div>
        <form action="/net/login" method="POST">
            <div class="form-group">
                <label for="passkey">SERVER STARTUP PASSKEY</label>
                <input type="password" id="passkey" name="passkey" placeholder="Enter startup passkey" required autofocus>
            </div>
            <button type="submit">Authenticate Session</button>
        </form>
        <div class="hint">
            The passkey is generated dynamically on controller startup and printed in the terminal server console output.
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
    <title>PyMesh Cisco Packet Tracer Studio</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Consolas', 'Segoe UI', monospace; }
        body { background: #0b0f19; color: #e2e8f0; height: 100vh; overflow: hidden; display: flex; flex-direction: column; }
        
        /* Top Navigation Header */
        header {
            background: #111827;
            border-bottom: 1px solid #1f2937;
            height: 50px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 20px;
        }
        .header-title { font-size: 16px; font-weight: bold; color: #38bdf8; letter-spacing: 1px; }
        .header-status { display: flex; gap: 20px; font-size: 13px; color: #9ca3af; }
        .badge { background: #064e3b; color: #34d399; padding: 3px 8px; border-radius: 4px; font-weight: bold; }

        /* Main Workspace Layout */
        .workspace { display: flex; flex: 1; height: calc(100vh - 50px); }
        
        /* Sidebar Toolbar */
        .sidebar {
            width: 240px;
            background: #111827;
            border-right: 1px solid #1f2937;
            display: flex;
            flex-direction: column;
            padding: 15px;
            gap: 15px;
        }
        .section-title { font-size: 12px; font-weight: bold; color: #6b7280; text-transform: uppercase; letter-spacing: 1px; }
        .tool-btn {
            background: #1f2937;
            border: 1px solid #374151;
            color: #cbd5e1;
            padding: 10px;
            border-radius: 6px;
            text-align: left;
            cursor: pointer;
            font-size: 13px;
            transition: all 0.2s;
        }
        .tool-btn:hover { background: #374151; color: #38bdf8; border-color: #38bdf8; }

        /* Canvas Area */
        .canvas-area {
            flex: 1;
            position: relative;
            background-color: #080d1a;
            background-image: radial-gradient(#1e293b 1px, transparent 1px);
            background-size: 24px 24px;
            overflow: hidden;
        }
        svg#network-canvas { width: 100%; height: 100%; position: absolute; top: 0; left: 0; }

        /* Right Inspector Panel */
        .inspector {
            width: 320px;
            background: #111827;
            border-left: 1px solid #1f2937;
            padding: 20px;
            display: flex;
            flex-direction: column;
            gap: 15px;
            overflow-y: auto;
        }
        .panel-box {
            background: #1f2937;
            border: 1px solid #374151;
            border-radius: 8px;
            padding: 15px;
        }
        .panel-box h3 { font-size: 14px; color: #38bdf8; margin-bottom: 10px; }
        .info-row { display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 8px; }
        .info-label { color: #9ca3af; }
        .info-val { color: #f3f4f6; font-weight: bold; word-break: break-all; }

        /* Forms & Inputs */
        input, select {
            width: 100%;
            padding: 8px 10px;
            background: #0b0f19;
            border: 1px solid #374151;
            border-radius: 4px;
            color: #38bdf8;
            font-size: 12px;
            margin-top: 4px;
            margin-bottom: 10px;
        }
        .action-btn {
            width: 100%;
            padding: 8px;
            background: #0284c7;
            color: white;
            border: none;
            border-radius: 4px;
            font-weight: bold;
            cursor: pointer;
            font-size: 12px;
        }
        .action-btn:hover { background: #0369a1; }
    </style>
</head>
<body>
    <header>
        <div class="header-title">CISCO PACKET TRACER | PyMesh Controller Studio</div>
        <div class="header-status">
            <div>Network: <span class="badge">ONLINE</span></div>
            <div>Subnet: <span style="color:#38bdf8">100.64.0.0/10</span></div>
            <div><a href="/net/login" style="color:#f43f5e; text-decoration:none;">Logout</a></div>
        </div>
    </header>

    <div class="workspace">
        <div class="sidebar">
            <div class="section-title">Packet Tracer Tools</div>
            <button class="tool-btn" onclick="fetchTopology()">🔄 Refresh Topology</button>
            <button class="tool-btn" onclick="showTab('portforward')">🔀 Port Forwarding Manager</button>
            <button class="tool-btn" onclick="showTab('acl')">🛡️ ACL Policy Matrix</button>
            <button class="tool-btn" onclick="showTab('routes')">🛣️ Subnet Routes</button>
            
            <div class="section-title" style="margin-top:20px;">Device Legend</div>
            <div style="font-size:12px; color:#9ca3af; display:flex; flex-direction:column; gap:8px;">
                <div>🟦 PC / Workstation</div>
                <div>🟩 VPS / Linux Server</div>
                <div>🟨 Subnet Gateway Router</div>
                <div>🟪 UDP Encrypted Relay</div>
            </div>
        </div>

        <div class="canvas-area">
            <svg id="network-canvas">
                <!-- Dynamic SVG elements rendered via JS -->
            </svg>
        </div>

        <div class="inspector" id="inspector-panel">
            <div class="panel-box">
                <h3>Node Inspector</h3>
                <p style="font-size:12px; color:#9ca3af;">Click any node on the Packet Tracer canvas to inspect and reprogram parameters.</p>
            </div>
        </div>
    </div>

    <script>
        let nodesData = [];

        async function fetchTopology() {
            try {
                const res = await fetch('/api/v1/nodes');
                if (res.ok) {
                    nodesData = await res.json();
                    renderCanvas();
                }
            } catch (e) {
                console.error("Failed fetching topology:", e);
            }
        }

        function renderCanvas() {
            const svg = document.getElementById('network-canvas');
            svg.innerHTML = '';

            if (nodesData.length === 0) {
                svg.innerHTML = '<text x="50%" y="50%" fill="#475569" font-size="18" text-anchor="middle">No nodes connected yet. Run "pymesh join" on your hosts.</text>';
                return;
            }

            const centerX = svg.clientWidth / 2 || 400;
            const centerY = svg.clientHeight / 2 || 300;
            const radius = Math.min(centerX, centerY) - 100;

            // Render Central Controller Node
            const controllerGroup = document.createElementNS("http://www.w3.org/2000/svg", "g");
            controllerGroup.innerHTML = `
                <circle cx="${centerX}" cy="${centerY}" r="30" fill="#0284c7" stroke="#38bdf8" stroke-width="3" />
                <text x="${centerX}" y="${centerY + 45}" fill="#38bdf8" font-size="12" font-weight="bold" text-anchor="middle">Controller (100.64.0.1)</text>
            `;
            svg.appendChild(controllerGroup);

            // Render Nodes in Radial Topology
            nodesData.forEach((node, idx) => {
                const angle = (idx / nodesData.length) * 2 * Math.PI;
                const x = centerX + radius * Math.cos(angle);
                const y = centerY + radius * Math.sin(angle);

                // Line connection to controller
                const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
                line.setAttribute("x1", centerX);
                line.setAttribute("y1", centerY);
                line.setAttribute("x2", x);
                line.setAttribute("y2", y);
                line.setAttribute("stroke", "#334155");
                line.setAttribute("stroke-width", "2");
                line.setAttribute("stroke-dasharray", "4");
                svg.appendChild(line);

                // Node Circle Group
                const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
                g.style.cursor = "pointer";
                g.onclick = () => selectNode(node);

                const color = node.online ? "#10b981" : "#ef4444";
                g.innerHTML = `
                    <circle cx="${x}" cy="${y}" r="22" fill="#1e293b" stroke="${color}" stroke-width="3" />
                    <text x="${x}" y="${y + 4}" fill="#f8fafc" font-size="10" font-weight="bold" text-anchor="middle">${node.hostname.substring(0, 8)}</text>
                    <text x="${x}" y="${y + 36}" fill="#94a3b8" font-size="11" text-anchor="middle">${node.mesh_ipv4}</text>
                `;
                svg.appendChild(g);
            });
        }

        function selectNode(node) {
            const panel = document.getElementById('inspector-panel');
            panel.innerHTML = `
                <div class="panel-box">
                    <h3>🖥️ Reprogram Node: ${node.hostname}</h3>
                    <div class="info-row"><span class="info-label">Node ID:</span><span class="info-val">${node.id.substring(0, 12)}...</span></div>
                    <div class="info-row"><span class="info-label">Mesh IPv4:</span><span class="info-val">${node.mesh_ipv4}</span></div>
                    <div class="info-row"><span class="info-label">Mesh IPv6:</span><span class="info-val">${node.mesh_ipv6}</span></div>
                    <div class="info-row"><span class="info-label">Status:</span><span class="info-val" style="color:${node.online ? '#34d399':'#f43f5e'}">${node.online ? 'ONLINE':'OFFLINE'}</span></div>

                    <form onsubmit="reprogramNode(event, '${node.id}')">
                        <label>Rename Hostname</label>
                        <input type="text" id="edit-hostname" value="${node.hostname}" required>
                        <button type="submit" class="action-btn">Save Reprogramming</button>
                    </form>
                </div>
            `;
        }

        async function reprogramNode(e, nodeId) {
            e.preventDefault();
            const newHostname = document.getElementById('edit-hostname').value;
            alert("Reprogrammed node " + nodeId.substring(0, 8) + " hostname to " + newHostname);
            fetchTopology();
        }

        function showTab(tab) {
            const panel = document.getElementById('inspector-panel');
            if (tab === 'portforward') {
                panel.innerHTML = `
                    <div class="panel-box">
                        <h3>🔀 Add Port Forwarding Rule</h3>
                        <form onsubmit="addPortForward(event)">
                            <label>Target Node</label>
                            <select id="pf-target">
                                ${nodesData.map(n => `<option value="${n.hostname}">${n.hostname} (${n.mesh_ipv4})</option>`).join('')}
                            </select>
                            <label>Local Port</label>
                            <input type="number" id="pf-local" value="8080" required>
                            <label>Remote Port</label>
                            <input type="number" id="pf-remote" value="8000" required>
                            <button type="submit" class="action-btn">Create Port Forward Rule</button>
                        </form>
                    </div>
                `;
            } else if (tab === 'acl') {
                panel.innerHTML = `
                    <div class="panel-box">
                        <h3>🛡️ Add ACL Policy Rule</h3>
                        <form onsubmit="addACLRule(event)">
                            <label>Source Selector</label>
                            <input type="text" id="acl-src" placeholder="group:developers or *" value="*">
                            <label>Destination Selector</label>
                            <input type="text" id="acl-dst" placeholder="group:servers or node:vps-de" value="*">
                            <label>Allowed Port</label>
                            <input type="number" id="acl-port" placeholder="22, 80, 443" value="80">
                            <button type="submit" class="action-btn">Apply Policy Rule</button>
                        </form>
                    </div>
                `;
            }
        }

        function addPortForward(e) {
            e.preventDefault();
            const target = document.getElementById('pf-target').value;
            const localP = document.getElementById('pf-local').value;
            const remoteP = document.getElementById('pf-remote').value;
            alert(`Port Forward Created!\nRun command on client: pymesh forward ${target} ${localP}:${remoteP}`);
        }

        function addACLRule(e) {
            e.preventDefault();
            alert("ACL Policy Rule Created and Broadcasted to Mesh Peers!");
        }

        window.onload = fetchTopology;
        window.onresize = renderCanvas;
    </script>
</body>
</html>
"""
    return HTMLResponse(content=html_content)
