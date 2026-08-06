"""
Rich terminal output formatting and topology graph renderers for PyMesh CLI.
"""

from typing import List, Dict, Any, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.tree import Tree

console = Console()


def print_status(node_info: Dict[str, Any], peers: List[Dict[str, Any]]) -> None:
    table = Table(title="PyMesh Local Status", show_header=True, header_style="bold cyan")
    table.add_column("Property", style="dim")
    table.add_column("Value")

    table.add_row("Node ID", node_info.get("node_id", "N/A"))
    table.add_row("Hostname", node_info.get("hostname", "N/A"))
    table.add_row("Mesh IPv4", node_info.get("mesh_ipv4", "N/A"))
    table.add_row("Mesh IPv6", node_info.get("mesh_ipv6", "N/A"))
    table.add_row("WireGuard Public Key", node_info.get("wireguard_public_key", "N/A"))
    table.add_row("Status", "[bold green]ONLINE[/bold green]" if node_info.get("online") else "[red]OFFLINE[/red]")
    table.add_row("Active Peers", str(len(peers)))

    console.print(table)


def print_netcheck(report: Dict[str, Any], peers: List[Dict[str, Any]]) -> None:
    console.print("\n[bold yellow]PyMesh Network Diagnostics[/bold yellow]\n")

    diag_table = Table(show_header=False, box=None)
    diag_table.add_column("Component", style="bold white", width=20)
    diag_table.add_column("Status")

    diag_table.add_row("IPv4", f"[bold green]{report.get('ipv4_status', 'OK')}[/bold green]")
    diag_table.add_row("IPv6", f"[bold green]{report.get('ipv6_status', 'OK')}[/bold green]")
    diag_table.add_row("UDP", f"[bold green]{report.get('udp_status', 'OK')}[/bold green]")
    diag_table.add_row("NAT", f"[cyan]{report.get('nat_type', 'Full Cone NAT')}[/cyan]")
    diag_table.add_row("Direct P2P", f"[bold green]{report.get('direct_p2p', 'Possible')}[/bold green]")
    diag_table.add_row("STUN", f"[bold green]{report.get('stun_status', 'OK')}[/bold green]")
    diag_table.add_row("Relay", f"[bold green]{report.get('relay_status', 'Available')}[/bold green]")

    console.print(diag_table)

    console.print("\n[bold cyan]Peers[/bold cyan]")
    peer_table = Table(show_header=True, header_style="bold magenta")
    peer_table.add_column("Peer Hostname")
    peer_table.add_column("Mesh IP")
    peer_table.add_column("Connection")
    peer_table.add_column("Latency")

    for p in peers:
        mode = p.get("mode", "DIRECT")
        mode_str = f"[bold green]{mode}[/bold green]" if mode == "DIRECT" else f"[yellow]{mode}[/yellow]"
        peer_table.add_row(
            p.get("hostname", "unknown"),
            p.get("mesh_ipv4", "100.64.0.x"),
            mode_str,
            f"{p.get('latency_ms', 12)} ms",
        )

    console.print(peer_table)
    console.print()


def print_topology(controller_url: str, nodes: List[Dict[str, Any]]) -> None:
    tree = Tree(f"[bold magenta]PyMesh Controller ({controller_url})[/bold magenta]")

    mesh_branch = tree.add("[bold cyan]Encrypted Private Mesh Network (100.64.0.0/10)[/bold cyan]")

    for node in nodes:
        hostname = node.get("hostname", "node")
        ip = node.get("mesh_ipv4", "100.64.0.x")
        status = "[bold green]ONLINE[/bold green]" if node.get("online", True) else "[red]OFFLINE[/red]"
        
        node_branch = mesh_branch.add(f"🖥️  [bold white]{hostname}[/bold white] ({ip}) - {status}")
        
        if node.get("endpoints"):
            node_branch.add(f"Endpoint: {node['endpoints'][0]}")
        if node.get("tags"):
            node_branch.add(f"Groups: {', '.join(node['tags'])}")

    console.print(Panel(tree, title="Network Topology Map", border_style="green"))
