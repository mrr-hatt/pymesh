"""
PyMesh Controller Entrypoint Server Application.
"""

from fastapi import FastAPI
from contextlib import asynccontextmanager

from pymesh.controller.api import router as api_router, db_manager
from pymesh.controller.web import router as web_router, print_startup_banner


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB tables on startup
    await db_manager.init_db()
    print_startup_banner()
    yield


app = FastAPI(
    title="PyMesh Controller API",
    description="Control Plane API for PyMesh private encrypted network",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(api_router)
app.include_router(web_router)


@app.get("/")
async def root():
    return {
        "service": "PyMesh Controller",
        "status": "running",
        "version": "0.1.0",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("controller.app:app", host="0.0.0.0", port=8000, reload=True)
