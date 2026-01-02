"""
MCP Server for zget.

Exposes video download, library search, and metadata extraction capabilities.
Run with: python -m zget.mcp.server
"""

import asyncio
import json
import sys
from typing import Any

from .tools import ZgetTools


class MCPServer:
    """
    Model Context Protocol server for zget.

    Implements the MCP stdio transport protocol for agent integration.
    """

    def __init__(self):
        self.tools = ZgetTools()
        self._running = False

    def _get_tool_list(self) -> list[dict]:
        """Return list of available tools in MCP format."""
        return [
            {
                "name": "zget_search",
                "description": "Search the zget video library using full-text search. Returns matching videos with titles, uploaders, and file paths.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query (supports prefix matching)",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum results to return (default: 20)",
                            "default": 20,
                        },
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "zget_get_video",
                "description": "Get full metadata for a video by its database ID.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "video_id": {
                            "type": "integer",
                            "description": "Database ID of the video",
                        },
                    },
                    "required": ["video_id"],
                },
            },
            {
                "name": "zget_get_local_path",
                "description": "Get the local file path for a video. Useful for passing to other tools that need the actual file.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "video_id": {
                            "type": "integer",
                            "description": "Database ID of the video",
                        },
                    },
                    "required": ["video_id"],
                },
            },
            {
                "name": "zget_download",
                "description": "Download a video from a URL to the local library. Returns the new video's metadata including local path.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "Video URL (YouTube, Twitter, Instagram, etc.)",
                        },
                        "collection": {
                            "type": "string",
                            "description": "Optional collection name to organize the video",
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional tags to apply",
                        },
                    },
                    "required": ["url"],
                },
            },
            {
                "name": "zget_extract_info",
                "description": "Extract metadata from a URL without downloading. Get title, uploader, duration, available formats.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "Video URL to inspect",
                        },
                    },
                    "required": ["url"],
                },
            },
            {
                "name": "zget_list_formats",
                "description": "List available download formats for a URL. Shows resolution, codec, and file size options.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "Video URL to check formats for",
                        },
                    },
                    "required": ["url"],
                },
            },
            {
                "name": "zget_check_url",
                "description": "Check if a URL is already in the library. Use before downloading to avoid duplicates.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "Video URL to check",
                        },
                    },
                    "required": ["url"],
                },
            },
            {
                "name": "zget_get_recent",
                "description": "Get recently downloaded videos from the library.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Maximum results (default: 20)",
                            "default": 20,
                        },
                    },
                },
            },
            {
                "name": "zget_get_by_uploader",
                "description": "Get all videos from a specific uploader/channel.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "uploader": {
                            "type": "string",
                            "description": "Uploader name to filter by",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum results (default: 50)",
                            "default": 50,
                        },
                    },
                    "required": ["uploader"],
                },
            },
        ]

    async def handle_request(self, request: dict) -> dict:
        """Handle an incoming MCP request."""
        method = request.get("method", "")
        req_id = request.get("id")
        params = request.get("params", {})

        try:
            if method == "initialize":
                return self._response(
                    req_id,
                    {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            "tools": {},
                        },
                        "serverInfo": {
                            "name": "zget",
                            "version": "0.3.0",
                        },
                    },
                )

            elif method == "tools/list":
                return self._response(req_id, {"tools": self._get_tool_list()})

            elif method == "tools/call":
                tool_name = params.get("name", "")
                arguments = params.get("arguments", {})
                result = await self._call_tool(tool_name, arguments)
                return self._response(
                    req_id,
                    {
                        "content": [{"type": "text", "text": json.dumps(result, indent=2)}],
                    },
                )

            elif method == "notifications/initialized":
                # Client notification, no response needed
                return None

            else:
                return self._error(req_id, -32601, f"Method not found: {method}")

        except Exception as e:
            return self._error(req_id, -32000, str(e))

    async def _call_tool(self, name: str, arguments: dict) -> Any:
        """Dispatch tool call to appropriate handler."""
        handlers = {
            "zget_search": self.tools.search,
            "zget_get_video": self.tools.get_video,
            "zget_get_local_path": self.tools.get_local_path,
            "zget_download": self.tools.download,
            "zget_extract_info": self.tools.extract_info,
            "zget_list_formats": self.tools.list_formats,
            "zget_check_url": self.tools.check_url,
            "zget_get_recent": self.tools.get_recent,
            "zget_get_by_uploader": self.tools.get_by_uploader,
        }

        handler = handlers.get(name)
        if not handler:
            raise ValueError(f"Unknown tool: {name}")

        return await handler(**arguments)

    def _response(self, req_id: Any, result: dict) -> dict:
        """Create a JSON-RPC response."""
        return {"jsonrpc": "2.0", "id": req_id, "result": result}

    def _error(self, req_id: Any, code: int, message: str) -> dict:
        """Create a JSON-RPC error response."""
        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}

    async def run(self):
        """Run the MCP server on stdio."""
        self._running = True
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin)

        writer_transport, writer_protocol = await asyncio.get_event_loop().connect_write_pipe(
            asyncio.streams.FlowControlMixin, sys.stdout
        )
        writer = asyncio.StreamWriter(
            writer_transport, writer_protocol, reader, asyncio.get_event_loop()
        )

        while self._running:
            try:
                # Read content-length header
                header = await reader.readline()
                if not header:
                    break

                header_str = header.decode().strip()
                if header_str.startswith("Content-Length:"):
                    length = int(header_str.split(":")[1].strip())
                    await reader.readline()  # Empty line
                    content = await reader.read(length)
                    request = json.loads(content.decode())

                    response = await self.handle_request(request)
                    if response:
                        response_bytes = json.dumps(response).encode()
                        writer.write(f"Content-Length: {len(response_bytes)}\r\n\r\n".encode())
                        writer.write(response_bytes)
                        await writer.drain()

            except asyncio.CancelledError:
                break
            except Exception as e:
                sys.stderr.write(f"MCP Server error: {e}\n")
                sys.stderr.flush()


def run_server():
    """Run the MCP server."""
    server = MCPServer()
    asyncio.run(server.run())


def main():
    """Entry point for zget-mcp command."""
    run_server()


if __name__ == "__main__":
    main()
