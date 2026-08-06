"""
Tests for Typer CLI commands invocation.
"""

import pytest
from typer.testing import CliRunner
from pymesh.cli.main import app

runner = CliRunner()


def test_cli_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "PyMesh" in result.stdout


def test_cli_netcheck():
    result = runner.invoke(app, ["netcheck"])
    assert result.exit_code == 0
    assert "PyMesh Network Diagnostics" in result.stdout
    assert "NAT" in result.stdout
    assert "Direct P2P" in result.stdout
