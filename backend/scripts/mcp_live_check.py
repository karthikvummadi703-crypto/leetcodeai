"""
Live MCP end-to-end check.

Boots ``python -m app.mcp.leetcode_server`` as a real stdio child process,
speaks MCP JSON-RPC to it, and calls all six tools against the live
``leetcode.com/graphql`` API. Prints each tool's raw text result.

Usage (from backend/):
    python scripts/mcp_live_check.py [username]

Manual QA tool — not part of the pytest suite.
"""

import asyncio
import json
import sys
from pathlib import Path

from mcp.client.stdio import stdio_client

from mcp import ClientSession, StdioServerParameters

BACKEND_DIR = Path(__file__).resolve().parent.parent

USERNAME = sys.argv[1] if len(sys.argv) > 1 else "StefanPochmann"


async def main() -> None:
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "app.mcp.leetcode_server"],
        cwd=str(BACKEND_DIR),
    )

    async with (
        stdio_client(params) as (read, write),
        ClientSession(read, write) as session,
    ):
        init = await session.initialize()
        print(
            f"== server booted: {init.serverInfo.name} v{init.serverInfo.version} "
            f"(protocol {init.protocolVersion})"
        )

        tools = await session.list_tools()
        print(f"== tools exposed ({len(tools.tools)}): {[t.name for t in tools.tools]}")

        calls = [
            ("get_leetcode_profile", {"username": USERNAME}),
            ("get_solved_problems", {"username": USERNAME, "limit": 5}),
            ("analyze_leetcode_account", {"username": USERNAME}),
            ("recommend_next_problems", {"username": USERNAME, "count": 3}),
            ("search_problems", {"query": "sliding window maximum", "limit": 3}),
            ("get_problem_detail", {"identifier": "1"}),
        ]

        for name, args in calls:
            print(f"\n{'=' * 78}\nCALL: {name}{json.dumps(args)}")
            try:
                result = await session.call_tool(name, args)
                if result.isError:
                    print(f"  !! TOOL ERROR: {result.content}")
                    continue
                for block in result.content:
                    if getattr(block, "type", None) == "text":
                        print(block.text)
                    else:
                        print(f"  [non-text block: {block}]")
            except Exception as exc:  # noqa: BLE001 — report any protocol failure
                print(f"  !! CALL FAILED: {type(exc).__name__}: {exc}")

    print("\n== stdio session closed cleanly")


if __name__ == "__main__":
    asyncio.run(main())
