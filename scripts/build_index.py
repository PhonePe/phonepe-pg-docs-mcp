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

#!/usr/bin/env python3
"""
build_index.py — Pre-build the SQLite FTS5 documentation index.

Reads docs_registry.yml, fetches all doc pages concurrently, and writes
the content to knowledge/doc_index.db (SQLite FTS5).

Run before every PyPI release:
    python scripts/build_index.py

Or in GitHub Actions:
    - name: Build doc index
      run: python scripts/build_index.py

The generated doc_index.db is committed to the repo and ships inside
the Python wheel so users get instant (sub-millisecond) doc lookups
without any network calls at runtime.
"""

from __future__ import annotations

import asyncio
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import httpx
    import yaml
    from bs4 import BeautifulSoup, Tag
except ImportError:
    print("Missing dependencies. Run: pip install httpx pyyaml beautifulsoup4")
    sys.exit(1)

# ── Paths ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
REGISTRY     = PROJECT_ROOT / "docs_registry.yml"
# Write directly into the package so it ships in the wheel
OUTPUT_DB    = PROJECT_ROOT / "src" / "phonepe_docs_mcp" / "knowledge" / "doc_index.db"

BASE_URL     = "https://developer.phonepe.com"
USER_AGENT   = "Mozilla/5.0 (compatible; PhonePe-PG-Docs-Indexer/1.0)"
CONCURRENCY  = 20   # parallel fetches
TIMEOUT      = 20.0

# ── Registry loader ─────────────────────────────────────────────────────────────

def load_registry() -> dict[str, str]:
    """Load section_key → url_path from docs_registry.yml."""
    if not REGISTRY.exists():
        print(f"ERROR: Registry file not found: {REGISTRY}")
        sys.exit(1)
    with REGISTRY.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    registry: dict[str, str] = {}
    for group in ("public", "additional"):
        for key, path in ((data or {}).get("sections", {}).get(group) or {}).items():
            if path:
                registry[str(key)] = str(path)
    return registry

# ── HTML → clean text ───────────────────────────────────────────────────────────

def extract_text(html: str) -> tuple[str, str]:
    """Return (title, clean_markdown_text) from raw HTML."""
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup.select(
        "nav, header, footer, script, style, img, "
        ".sidebar, .toc, .breadcrumb, .pagination"
    ):
        tag.decompose()

    # Extract page title
    title_tag = soup.find("h1") or soup.find("title")
    title = title_tag.get_text(" ", strip=True) if title_tag else ""

    root: Tag = (
        soup.find("main")
        or soup.find("article")
        or soup.find(id="content")
        or soup.body  # type: ignore[assignment]
    )
    if root is None:
        return title, ""

    parts: list[str] = []
    for el in root.find_all(["h1", "h2", "h3", "h4", "p", "li", "td", "th", "code", "pre"]):
        text = el.get_text(" ", strip=True)
        if not text:
            continue
        tag_name = el.name
        if tag_name == "h1":
            parts.append(f"# {text}")
        elif tag_name == "h2":
            parts.append(f"## {text}")
        elif tag_name == "h3":
            parts.append(f"### {text}")
        elif tag_name == "h4":
            parts.append(f"#### {text}")
        elif tag_name in ("pre", "code"):
            parts.append(f"```\n{text}\n```")
        elif tag_name == "li":
            parts.append(f"- {text}")
        elif tag_name == "th":
            parts.append(f"**{text}**")
        else:
            parts.append(text)

    content = "\n\n".join(parts).strip()
    content = re.sub(r"(\n\s*){3,}", "\n\n", content)
    return title, content

# ── Async fetch ─────────────────────────────────────────────────────────────────

async def fetch_one(
    client: httpx.AsyncClient,
    sem: asyncio.Semaphore,
    section_key: str,
    url_path: str,
) -> tuple[str, str, str, str]:
    """Fetch a single page. Returns (section_key, url_path, title, content)."""
    url = BASE_URL + url_path
    async with sem:
        try:
            resp = await client.get(url, follow_redirects=True)
            resp.raise_for_status()
            title, content = extract_text(resp.text)
            return section_key, url_path, title, content
        except Exception as exc:
            print(f"  ⚠  SKIP {section_key}: {exc}")
            return section_key, url_path, "", ""

# ── SQLite setup ────────────────────────────────────────────────────────────────

def create_db(db_path: Path) -> sqlite3.Connection:
    """Create (or recreate) the SQLite database with FTS5."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")

    conn.executescript("""
        CREATE TABLE doc_sections (
            section_key  TEXT PRIMARY KEY,
            url_path     TEXT NOT NULL,
            title        TEXT,
            content      TEXT,
            indexed_at   TEXT
        );

        CREATE VIRTUAL TABLE doc_fts USING fts5(
            section_key  UNINDEXED,
            title,
            content,
            content      = 'doc_sections',
            content_rowid = 'rowid',
            tokenize     = 'porter ascii'
        );

        CREATE TRIGGER doc_sections_ai AFTER INSERT ON doc_sections BEGIN
            INSERT INTO doc_fts(rowid, section_key, title, content)
            VALUES (new.rowid, new.section_key, new.title, new.content);
        END;
    """)
    conn.commit()
    return conn

# ── Main ────────────────────────────────────────────────────────────────────────

async def main() -> None:
    print(f"PhonePe PG Doc Indexer")
    print(f"Registry : {REGISTRY}")
    print(f"Output   : {OUTPUT_DB}")
    print()

    registry = load_registry()
    total = len(registry)
    print(f"Sections : {total}")

    sem = asyncio.Semaphore(CONCURRENCY)
    headers = {"User-Agent": USER_AGENT}
    now = datetime.now(timezone.utc).isoformat()

    async with httpx.AsyncClient(headers=headers, timeout=TIMEOUT) as client:
        tasks = [
            fetch_one(client, sem, key, path)
            for key, path in registry.items()
        ]
        print(f"Fetching {total} pages with {CONCURRENCY} concurrent workers...\n")
        results = await asyncio.gather(*tasks)

    print(f"\nBuilding SQLite FTS5 index at {OUTPUT_DB} ...")
    conn = create_db(OUTPUT_DB)

    ok = 0
    for section_key, url_path, title, content in results:
        if not content:
            continue
        conn.execute(
            "INSERT INTO doc_sections (section_key, url_path, title, content, indexed_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (section_key, url_path, title, content, now),
        )
        ok += 1

    conn.commit()

    # Optimize FTS index
    conn.execute("INSERT INTO doc_fts(doc_fts) VALUES ('optimize')")
    conn.commit()

    # Checkpoint WAL so the .db file is self-contained when packaged in the wheel
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    conn.commit()
    conn.close()

    db_size_kb = OUTPUT_DB.stat().st_size / 1024
    print(f"\n✅ Done!")
    print(f"   Indexed : {ok}/{total} sections")
    print(f"   Skipped : {total - ok} sections (fetch errors)")
    print(f"   DB size : {db_size_kb:.0f} KB ({db_size_kb/1024:.1f} MB)")
    print(f"   Path    : {OUTPUT_DB}")


if __name__ == "__main__":
    asyncio.run(main())
