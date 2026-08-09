"""
TLD Validation, Registry Engine, and registry.{tld} Web Page Generator.
"""

import re
import json
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("pymesh.tld")


class TLDManager:
    """Manages custom Top-Level Domain (TLD) publishing and DNS validation."""

    @staticmethod
    def clean_tld(tld_input: str) -> str:
        """Strips leading dots and lowercases the TLD string."""
        return tld_input.lstrip(".").strip().lower()

    @staticmethod
    def validate_tld_name(tld_input: str) -> bool:
        """
        Validates TLD name against RFC 1035 standards for standard browser readability.
        Must be 2-24 characters, contain only a-z, 0-9, or hyphens, and not start/end with hyphen.
        Rejects non-standard/absurd TLD strings.
        """
        clean = TLDManager.clean_tld(tld_input)
        if len(clean) < 2 or len(clean) > 24:
            return False
        
        # Must match label pattern: letters, numbers, hyphens (cannot start/end with hyphen)
        pattern = r"^[a-z0-9]([a-z0-9-]{0,22}[a-z0-9])?$"
        if not re.match(pattern, clean):
            return False

        # Reserved / dangerous names to avoid browser collision
        reserved = {"localhost", "invalid", "local", "arpa", "test", "example", "com", "net", "org"}
        if clean in reserved:
            return False

        return True

    @staticmethod
    def render_registry_html(tld_name: str, publisher_details: str, registered_domains: List[Dict[str, Any]]) -> str:
        """Renders HTML page for registry.{tld}."""
        clean = TLDManager.clean_tld(tld_name)
        
        domain_rows = ""
        for d in registered_domains:
            domain_rows += f"""
            <tr>
                <td><b>{d.get('hostname')}.{clean}</b></td>
                <td>{d.get('mesh_ipv4')}</td>
                <td>{d.get('mesh_ipv6', 'N/A')}</td>
                <td><span class="status-active">ACTIVE</span></td>
            </tr>
            """

        if not domain_rows:
            domain_rows = f"<tr><td colspan='4' style='text-align:center; color:#666;'>No registered nodes in .{clean} yet.</td></tr>"

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TLD Registry | .{clean}</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }}
        body {{ background: #f8fafc; color: #0f172a; padding: 40px 20px; line-height: 1.6; }}
        .container {{ max-width: 800px; margin: 0 auto; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 30px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }}
        .header {{ border-bottom: 2px solid #0284c7; padding-bottom: 15px; margin-bottom: 25px; }}
        .header h1 {{ font-size: 28px; color: #0284c7; }}
        .header p {{ color: #64748b; font-size: 14px; margin-top: 4px; }}
        .info-card {{ background: #f1f5f9; border-left: 4px solid #0284c7; padding: 15px 20px; margin-bottom: 25px; border-radius: 0 6px 6px 0; }}
        .info-card h3 {{ font-size: 16px; color: #0f172a; margin-bottom: 6px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 14px; }}
        th, td {{ border: 1px solid #cbd5e1; padding: 10px 12px; text-align: left; }}
        th {{ background: #e2e8f0; color: #334155; font-weight: 600; }}
        .status-active {{ background: #dcfce7; color: #166534; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Top-Level Domain Registry: .{clean}</h1>
            <p>PyMesh Encrypted Private Mesh Network TLD Information Page</p>
        </div>
        <div class="info-card">
            <h3>TLD Publisher Information</h3>
            <p>{publisher_details}</p>
        </div>
        <h2>Registered .{clean} Hostnames</h2>
        <table>
            <thead>
                <tr>
                    <th>Domain Name</th>
                    <th>Mesh IPv4</th>
                    <th>Mesh IPv6</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
                {domain_rows}
            </tbody>
        </table>
    </div>
</body>
</html>"""
        return html
