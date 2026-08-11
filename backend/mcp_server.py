"""
Standalone LeetCode MCP server entry point.

Lets any MCP client connect to the app's LeetCode account tools.

    python mcp_server.py              # stdio transport (default)
    python mcp_server.py --sse        # SSE transport on :8001

For Claude Desktop add a server entry such as:

    "leetcode-guidance": {
        "command": "python",
        "args": ["path/to/backend/mcp_server.py"]
    }
"""

from app.mcp.leetcode_server import main

if __name__ == "__main__":
    main()
