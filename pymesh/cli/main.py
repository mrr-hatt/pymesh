"""
Main Typer CLI Application for PyMesh.
"""

import typer
from typing import Optional
from pathlib import Path

from pymesh.cli import commands

app = typer.Typer(
    name="pymesh",
    help="PyMesh - Encrypted Private Mesh Network CLI",
    add_completion=False,
)

route_app = typer.Typer(help="Manage subnet routes and exit nodes")
app.add_typer(route_app, name="route")


@app.command("join")
def join(
    controller_url: str = typer.Argument(..., help="Controller URL (e.g. http://mesh.example.com:8000)"),
    token: Optional[str] = typer.Option(None, "--token", "-t", help="Join authentication token"),
    hostname: Optional[str] = typer.Option(None, "--hostname", "-h", help="Custom node hostname"),
):
    """Register machine with a PyMesh controller."""
    commands.handle_join(controller_url, token, hostname)


@app.command("up")
def up():
    """Bring the PyMesh network interface UP."""
    commands.handle_up()


@app.command("down")
def down():
    """Bring the PyMesh network interface DOWN."""
    commands.handle_down()


@app.command("status")
def status():
    """Display current PyMesh node status and connection info."""
    commands.handle_status()


@app.command("nodes")
def nodes():
    """List all registered nodes and mesh network topology."""
    commands.handle_nodes()


@app.command("peers")
def peers():
    """List active WireGuard peer connections."""
    commands.handle_status()


@app.command("ping")
def ping(target: str = typer.Argument(..., help="Target node hostname or mesh IP")):
    """Ping a node across the PyMesh network."""
    commands.handle_ping(target)


@app.command("ssh")
def ssh(target: str = typer.Argument(..., help="Target node hostname or mesh IP")):
    """SSH directly into a node across the mesh."""
    commands.handle_ssh(target)


@app.command("netcheck")
def netcheck():
    """Run comprehensive network diagnostics (NAT type, STUN, Relay, P2P status)."""
    commands.handle_netcheck()


@app.command("topology")
def topology():
    """Visualize the active PyMesh mesh network topology."""
    commands.handle_nodes()


@app.command("key")
def key():
    """Display public keys and cryptographic node identity."""
    commands.handle_key()


@app.command("identity")
def identity():
    """Display cryptographic node identity details."""
    commands.handle_key()


@app.command("forward")
def forward(
    target: str = typer.Argument(..., help="Target node hostname or mesh IP (e.g. SV1)"),
    ports: str = typer.Argument(..., help="Ports format local:remote or port (e.g. 8000 or 8080:8000)"),
):
    """Forward a local port (e.g. localhost:8000) over the mesh to a remote node."""
    commands.handle_forward(target, ports)


@route_app.command("add")
def route_add(
    subnet: str = typer.Argument(..., help="Subnet CIDR (e.g. 10.10.0.0/24)"),
    via: str = typer.Option(..., "--via", "-v", help="Router node hostname or ID"),
):
    """Add a subnet route via a specified router node."""
    commands.handle_route_add(subnet, via)


if __name__ == "__main__":
    app()
