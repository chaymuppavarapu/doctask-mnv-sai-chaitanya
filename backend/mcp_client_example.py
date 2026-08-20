"""Runnable Streamable-HTTP MCP workflow client.

Start ``mcp_server.py`` first, then:
``python mcp_client_example.py --project-id 1 --document-ids 2 3``.
"""
from __future__ import annotations

import argparse
import asyncio
import json

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


async def run(url: str, project_id: int, document_ids: list[int]) -> None:
    async with streamable_http_client(url) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            created = await session.call_tool("create_analysis_run", {
                "project_id": project_id, "document_ids": document_ids,
            })
            print("create_analysis_run:", created)
            # MCP responses expose JSON as a text content item with this server.
            payload = json.loads(created.content[0].text)
            run_id = payload["run_id"]
            run_state = await session.call_tool("get_run", {"run_id": run_id})
            print("get_run:", run_state)
            report = await session.call_tool("get_report", {"run_id": run_id})
            print("get_report:", report)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:9001/mcp")
    parser.add_argument("--project-id", type=int, required=True)
    parser.add_argument("--document-ids", type=int, nargs="+", required=True)
    args = parser.parse_args()
    asyncio.run(run(args.url, args.project_id, args.document_ids))


if __name__ == "__main__":
    main()
