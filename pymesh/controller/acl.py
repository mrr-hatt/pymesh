"""
ACL (Access Control List) policy evaluation engine for PyMesh networks.
"""

from typing import List, Dict, Any, Optional


class ACLEngine:
    """Evaluates fine-grained access control rules between mesh nodes."""

    def __init__(self, rules: Optional[List[Dict[str, Any]]] = None):
        self.rules = rules or []

    def set_rules(self, rules: List[Dict[str, Any]]) -> None:
        self.rules = rules

    def is_allowed(
        self,
        src_node: Dict[str, Any],
        dst_node: Dict[str, Any],
        port: Optional[int] = None,
        protocol: str = "tcp",
    ) -> bool:
        """Determines if src_node is authorized to communicate with dst_node."""
        if not self.rules:
            # Default allow if no ACL rules configured
            return True

        for rule in self.rules:
            if self._match_rule(rule, src_node, dst_node, port, protocol):
                return rule.get("action", "allow") == "allow"

        # Default deny if rules exist but none match
        return False

    def _match_rule(
        self,
        rule: Dict[str, Any],
        src_node: Dict[str, Any],
        dst_node: Dict[str, Any],
        port: Optional[int] = None,
        protocol: str = "tcp",
    ) -> bool:
        src_pattern = rule.get("source", "*")
        dst_pattern = rule.get("destination", "*")

        if not self._match_node_selector(src_pattern, src_node):
            return False

        if not self._match_node_selector(dst_pattern, dst_node):
            return False

        rule_ports = rule.get("ports", [])
        if rule_ports and port is not None and port not in rule_ports:
            return False

        rule_protocols = rule.get("protocols", [])
        if rule_protocols and protocol not in rule_protocols:
            return False

        return True

    def _match_node_selector(self, selector: str, node: Dict[str, Any]) -> bool:
        if selector == "*":
            return True

        if selector.startswith("group:"):
            group_name = selector.split(":", 1)[1]
            return group_name in node.get("tags", [])

        if selector.startswith("node:"):
            target = selector.split(":", 1)[1]
            return target in (node.get("hostname"), node.get("node_id"), node.get("mesh_ipv4"))

        return selector in (node.get("hostname"), node.get("node_id"), node.get("mesh_ipv4"))
