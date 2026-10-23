"""Every runtime tool handler must be exposed by mcp/server.py.

mcp/server.py cannot always be imported in tests (it needs the optional `mcp`
extra, and mcp 2.x removed the decorator API it uses), so the registry is
parsed from source text instead.
"""
import re
from pathlib import Path

from capital_os.runtime.execute_tool import TOOL_HANDLERS

SERVER = Path(__file__).resolve().parents[2] / "mcp" / "server.py"


def _registry_names() -> set[str]:
    text = SERVER.read_text()
    block = text.split("_TOOL_REGISTRY", 1)[1].split("\n]\n", 1)[0]
    return set(re.findall(r'^\s*\("(\w+)",\s*\w+,', block, re.M))


def test_mcp_registry_matches_tool_handlers():
    names = _registry_names()
    assert names == set(TOOL_HANDLERS), {
        "missing_from_mcp": sorted(set(TOOL_HANDLERS) - names),
        "unknown_in_mcp": sorted(names - set(TOOL_HANDLERS)),
    }
