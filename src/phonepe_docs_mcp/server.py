# Copyright 2026 PhonePe Private Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
PhonePe PG Docs MCP Server — documentation and knowledge base entrypoint.

Exposes PhonePe Payment Gateway developer documentation and a curated
knowledge base to AI agents. No PhonePe credentials required.

📚 Documentation tools (scraped from developer.phonepe.com):
  list_doc_sections    – list all 244+ available doc sections
  get_section_content  – fetch full content of a specific section
  search_docs          – keyword search across all sections (SQLite FTS5 — fast)
  get_api_endpoints    – quick reference table of all API endpoints
  get_prerequisites    – setup requirements per integration type
  get_environments     – sandbox and production base URLs

🧠 Knowledge base tools (instant — no scraping):
  ask_knowledge_base   – answer any product/feature/API question
  list_products        – all live PhonePe PG products
  get_feature_support  – "does PhonePe support X?"
  get_error_code_info  – error cause and resolution

Optional env var:
  PHONEPE_DOCS_CACHE_TTL_SECONDS – cache TTL for live-fetched pages (default 3600)
"""

from __future__ import annotations

import os
import sys
import threading
from io import TextIOWrapper
from pathlib import Path

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv(Path(__file__).parent.parent.parent / ".env", override=False)

from .tools.doc_tools import register_doc_tools, register_kb_tools  # noqa: E402

mcp = FastMCP(
    name="phonepe-pg-docs",
    instructions=(
        "PhonePe Payment Gateway — Documentation & Knowledge Base MCP.\n\n"
        "No credentials required. All tools provide read-only information.\n\n"
        "RECOMMENDED TOOL SELECTION:\n"
        "  For product/feature questions ('does PhonePe support X', 'what products exist'):\n"
        "    → ask_knowledge_base  OR  list_products  OR  get_feature_support\n\n"
        "  For API endpoint questions ('what API checks chargeback', 'order status API'):\n"
        "    → ask_knowledge_base  (checks knowledge base + API quick reference)\n\n"
        "  For error code questions ('what is AUTHORIZATION_FAILED'):\n"
        "    → get_error_code_info\n\n"
        "  For detailed integration guides or request/response schemas:\n"
        "    → list_doc_sections → get_section_content\n"
        "    → search_docs (keyword search, instant via SQLite FTS5 index)\n\n"
        "  For environment URLs and prerequisites:\n"
        "    → get_environments  OR  get_prerequisites\n\n"
        "For live payment API calls, install the companion MCP: phonepe-pg-payments-mcp"
    ),
)

register_doc_tools(mcp)
register_kb_tools(mcp)


def _filter_stdin_empty_lines() -> None:
    """Drop bare newline / whitespace-only lines from stdin before the MCP
    JSON-RPC parser sees them.

    Some MCP clients (Claude Desktop, VS Code Extension, etc.) send empty
    lines between JSON-RPC messages as keepalives or line-termination
    artefacts.  The mcp library's stdio transport tries to parse every line as
    JSON and logs ``Invalid JSON: EOF`` validation errors for those lines.
    Filtering them out here — before the library's transport is created —
    prevents that noise entirely.

    A daemon thread forwards non-empty lines from the original stdin fd
    through an OS pipe.  fd 0 is then redirected to the read-end of that pipe
    so all downstream readers (asyncio / anyio) transparently receive a clean
    byte stream.
    """
    try:
        original_stdin_fd = sys.stdin.fileno()
    except Exception:
        return  # stdin is not a real file descriptor — nothing to filter

    pipe_r_fd, pipe_w_fd = os.pipe()

    # Preserve a copy of the original stdin fd for the reader thread so it
    # can keep reading after fd 0 is re-pointed at the pipe.
    src_fd = os.dup(original_stdin_fd)

    # Redirect fd 0 to the read-end of the pipe.
    os.dup2(pipe_r_fd, original_stdin_fd)
    os.close(pipe_r_fd)

    def _forward(src_fd: int, dst_fd: int) -> None:
        remainder = b""
        try:
            with os.fdopen(src_fd, "rb", buffering=0) as src, \
                    os.fdopen(dst_fd, "wb", buffering=0) as dst:
                while True:
                    chunk = src.read(4096)
                    if not chunk:           # EOF
                        if remainder.strip():
                            dst.write(remainder)
                        break
                    remainder += chunk
                    while b"\n" in remainder:
                        line, remainder = remainder.split(b"\n", 1)
                        if line.strip():    # skip empty / whitespace-only lines
                            dst.write(line + b"\n")
        except Exception:
            pass  # never let a filter error crash the server

    threading.Thread(
        target=_forward,
        args=(src_fd, pipe_w_fd),
        daemon=True,
        name="stdin-empty-line-filter",
    ).start()

    # Re-attach sys.stdin to fd 0, which now points at the clean pipe.
    sys.stdin = TextIOWrapper(
        open(original_stdin_fd, "rb"),
        encoding="utf-8",
        errors="replace",
    )


def main() -> None:
    """Run the MCP server over stdio."""
    _filter_stdin_empty_lines()
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
