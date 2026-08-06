"""
Tests for IPAllocator mesh address assignment.
"""

import pytest
from pymesh.controller.allocator import IPAllocator


def test_ip_allocator_sequential():
    allocator = IPAllocator(ipv4_cidr="100.64.0.0/10", ipv6_cidr="fd00:7079:6d65::/48")
    
    allocated_v4 = set()
    allocated_v6 = set()

    v4_1, v6_1 = allocator.allocate(allocated_v4, allocated_v6)
    assert v4_1 == "100.64.0.2" # .1 reserved for controller
    assert v6_1.startswith("fd00:7079:6d65::")

    allocated_v4.add(v4_1)
    allocated_v6.add(v6_1)

    v4_2, v6_2 = allocator.allocate(allocated_v4, allocated_v6)
    assert v4_2 == "100.64.0.3"
    assert v4_2 != v4_1
