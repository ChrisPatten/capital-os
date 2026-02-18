#!/usr/bin/env python3
"""Smoke test for the MCP server: validates it can list tools."""
import asyncio
import json
import subprocess
import sys
import time


async def test_mcp_server():
    """Test the MCP server by sending initialize + tools/list."""
    # Start the container
    proc = subprocess.Popen(
        ["docker", "run", "-i", "--rm", "-v", "capital-os-data:/app/data", "capital-os-mcp"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    try:
        # Send initialize request
        init_req = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "smoke-test", "version": "1.0"},
            },
        }
        print("[TEST] Sending initialize...")
        proc.stdin.write(json.dumps(init_req) + "\n")
        proc.stdin.flush()

        # Wait a bit for response
        await asyncio.sleep(2)

        # Send tools/list request
        list_req = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {},
        }
        print("[TEST] Sending tools/list...")
        proc.stdin.write(json.dumps(list_req) + "\n")
        proc.stdin.flush()

        # Read response (with timeout)
        start = time.time()
        response_lines = []
        while time.time() - start < 10:  # 10 second timeout
            line = proc.stdout.readline()
            if not line:
                await asyncio.sleep(0.1)
                continue
            response_lines.append(line)
            try:
                resp = json.loads(line)
                if resp.get("id") == 2:  # tools/list response
                    print("[PASS] Received tools/list response!")
                    tools = resp.get("result", {}).get("tools", [])
                    print(f"[INFO] Total tools available: {len(tools)}")
                    if len(tools) == 25:
                        print("[PASS] All 25 tools present!")
                        return True
                    else:
                        print(f"[FAIL] Expected 25 tools, got {len(tools)}")
                        return False
            except json.JSONDecodeError:
                pass

        print("[FAIL] No tools/list response received within timeout")
        return False

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    result = asyncio.run(test_mcp_server())
    sys.exit(0 if result else 1)
