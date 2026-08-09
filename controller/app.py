"""
PyMesh Controller Entrypoint Server Application.
"""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager

from pymesh.controller.api import router as api_router, db_manager


import logging

logger = logging.getLogger("pymesh.controller")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB tables on startup
    await db_manager.init_db()

    # Auto-start PyMesh DNS Server for custom TLDs (*.cr, *.mesh)
    from pymesh.dns.server import PyMeshDNSServer
    dns_srv = PyMeshDNSServer("0.0.0.0", 53, "http://localhost:8000")
    try:
        await dns_srv.start()
        print(f"========================================================")
        print(f" PyMesh Controller API running on http://0.0.0.0:8000")
        print(f" PyMesh DNS Server active on UDP 0.0.0.0:{dns_srv.bind_port}")
        print(f" Custom TLDs (*.cr, *.mesh, registry.cr) Ready")
        print(f"========================================================")
    except Exception as e:
        logger.warning(f"Could not auto-start DNS server on port 53: {e}")

    app.state.dns_srv = dns_srv
    yield

    dns_srv.stop()


app = FastAPI(
    title="PyMesh Controller API",
    description="Control Plane API for PyMesh private encrypted network",
    version="0.2.0",
    lifespan=lifespan,
)

app.include_router(api_router)


@app.get("/")
async def root():
    return {
        "service": "PyMesh Controller",
        "status": "running",
        "version": "0.2.0",
    }


@app.get("/registry/{tld_name}", response_class=HTMLResponse)
async def registry_tld_page(tld_name: str):
    from fastapi.responses import HTMLResponse
    from sqlalchemy import select
    from pymesh.dns.tld import TLDManager
    from pymesh.storage.models import TLDRegistry, NodeModel

    clean = TLDManager.clean_tld(tld_name)
    async for db in db_manager.get_session():
        stmt = select(TLDRegistry).where(TLDRegistry.name == clean)
        res = await db.execute(stmt)
        tld_entry = res.scalar_one_or_none()

        publisher_info = tld_entry.publisher_info if tld_entry else f"Official .{clean} TLD Registry"

        n_stmt = select(NodeModel)
        n_res = await db.execute(n_stmt)
        nodes = n_res.scalars().all()
        nodes_list = [{"hostname": n.hostname, "mesh_ipv4": n.mesh_ipv4, "mesh_ipv6": n.mesh_ipv6} for n in nodes]

        return HTMLResponse(content=TLDManager.render_registry_html(clean, publisher_info, nodes_list))


@app.get("/dns-query")
@app.post("/dns-query")
async def doh_dns_query(request: Request):
    from fastapi import Response
    import base64

    dns_srv = getattr(app.state, "dns_srv", None)
    if not dns_srv:
        from pymesh.dns.server import PyMeshDNSServer
        dns_srv = PyMeshDNSServer("0.0.0.0", 53, "http://localhost:8000")

    query_bytes = b""
    if request.method == "POST":
        query_bytes = await request.body()
    elif request.method == "GET":
        dns_param = request.query_params.get("dns")
        if dns_param:
            padded = dns_param + "=" * (-len(dns_param) % 4)
            try:
                query_bytes = base64.urlsafe_b64decode(padded)
            except Exception:
                pass

    if not query_bytes:
        return Response(status_code=400, content="Missing DNS query message")

    response_bytes = await dns_srv.process_query_data(query_bytes)
    return Response(content=response_bytes, media_type="application/dns-message")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("controller.app:app", host="0.0.0.0", port=8000, reload=True)
