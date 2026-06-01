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
PhonePe developer-documentation service.

Two-tier lookup:
  Tier 1 (fast): SQLite FTS5 index bundled in the package — sub-millisecond
  Tier 2 (slow): Live web scraping — used only when a section is missing from the index

The SQLite index (doc_index.db) is pre-built by scripts/build_index.py, committed
to the repo inside src/phonepe_docs_mcp/knowledge/, and shipped in the Python wheel.

Section registry is maintained in docs_registry.yml.
No code changes are needed to add new sections — just edit that file and restart.
"""

from __future__ import annotations

import atexit
import logging
import re
import sqlite3
import threading
import time
from pathlib import Path
from typing import Dict, Optional, Tuple

import httpx
import yaml
from bs4 import BeautifulSoup, Tag

from ..config import config
from ._paths import INDEX_DB as _INDEX_DB, REGISTRY_FILE as _REGISTRY_FILE

logger = logging.getLogger(__name__)

_BASE_URL  = "https://developer.phonepe.com"
_USER_AGENT = "Mozilla/5.0 (compatible; PhonePe-PG-Docs-MCP/1.0)"
_TIMEOUT   = 15.0


# ──────────────────────────────────────────────────────────────────────────────
# Registry loader
# ──────────────────────────────────────────────────────────────────────────────

def _load_registry() -> Dict[str, str]:
    if not _REGISTRY_FILE.exists():
        return {}
    with _REGISTRY_FILE.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    registry: Dict[str, str] = {}
    for group in ("public", "additional"):
        for key, path in ((data or {}).get("sections", {}).get(group) or {}).items():
            if path:
                registry[str(key)] = str(path)
    return registry


_SECTION_REGISTRY: Dict[str, str] = _load_registry()


# ──────────────────────────────────────────────────────────────────────────────
# SQLite index connection (lazy, read-only, thread-safe)
# ──────────────────────────────────────────────────────────────────────────────

_db_conn: Optional[sqlite3.Connection] = None
_db_lock = threading.Lock()


def _get_db() -> Optional[sqlite3.Connection]:
    global _db_conn
    if _db_conn is not None:
        return _db_conn
    with _db_lock:
        # Double-checked locking: another thread may have initialised between
        # our first check and acquiring the lock.
        if _db_conn is not None:
            return _db_conn
        if not _INDEX_DB.exists():
            return None
        try:
            _db_conn = sqlite3.connect(
                f"file:{_INDEX_DB}?mode=ro", uri=True, check_same_thread=False
            )
            _db_conn.row_factory = sqlite3.Row
            return _db_conn
        except Exception as exc:
            logger.warning("Failed to open SQLite index at %s: %s", _INDEX_DB, exc)
            return None


def _close_db() -> None:
    global _db_conn
    if _db_conn is not None:
        try:
            _db_conn.close()
        except Exception:
            pass
        _db_conn = None


atexit.register(_close_db)


# ──────────────────────────────────────────────────────────────────────────────
# HTML → clean text (used only for live fallback)
# ──────────────────────────────────────────────────────────────────────────────

def _extract_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.select(
        "nav, header, footer, script, style, img, "
        ".sidebar, .toc, .breadcrumb, .pagination"
    ):
        tag.decompose()
    root: Tag = (
        soup.find("main")
        or soup.find("article")
        or soup.find(id="content")
        or soup.body  # type: ignore[assignment]
    )
    if root is None:
        return ""
    parts: list[str] = []
    for el in root.find_all(["h1", "h2", "h3", "h4", "p", "li", "td", "th", "code", "pre"]):
        text = el.get_text(" ", strip=True)
        if not text:
            continue
        t = el.name
        if t == "h1":              parts.append(f"# {text}")
        elif t == "h2":            parts.append(f"## {text}")
        elif t == "h3":            parts.append(f"### {text}")
        elif t == "h4":            parts.append(f"#### {text}")
        elif t in ("pre", "code"): parts.append(f"```\n{text}\n```")
        elif t == "li":            parts.append(f"- {text}")
        elif t == "th":            parts.append(f"**{text}**")
        else:                      parts.append(text)
    content = "\n\n".join(parts).strip()
    return re.sub(r"(\n\s*){3,}", "\n\n", content)


def _live_fetch(section_key: str) -> str:
    path = _SECTION_REGISTRY.get(section_key)
    if path is None:
        raise ValueError(
            f"Unknown section key: '{section_key}'. "
            "Use list_doc_sections to see available sections."
        )
    url = _BASE_URL + path
    try:
        resp = httpx.get(url, headers={"User-Agent": _USER_AGENT}, timeout=_TIMEOUT, follow_redirects=True)
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise RuntimeError(f"Failed to fetch doc page (HTTP {exc.response.status_code}): {url}") from exc
    except httpx.RequestError as exc:
        raise RuntimeError(f"Network error fetching doc page: {url} — {exc}") from exc
    return _extract_text(resp.text)


def _snippet(content: str, keyword: str) -> str:
    idx = content.lower().find(keyword)
    if idx < 0:
        return ""
    start = max(0, idx - 150)
    end = min(len(content), idx + 300)
    return "..." + content[start:end].strip() + "..."


# ──────────────────────────────────────────────────────────────────────────────
# Main service class
# ──────────────────────────────────────────────────────────────────────────────

class DocService:
    def __init__(self) -> None:
        db = _get_db()
        if db:
            try:
                self._index_count: int = db.execute(
                    "SELECT COUNT(*) FROM doc_sections"
                ).fetchone()[0]
            except Exception as exc:
                logger.warning("Failed to count doc_sections in index: %s", exc)
                self._index_count = 0
        else:
            self._index_count = 0

        # In-memory cache: section_key → (content, cached_at)
        # Entries older than config.docs_cache_ttl_seconds are re-fetched.
        self._live_cache: Dict[str, Tuple[str, float]] = {}
        # Protects _live_cache from TOCTOU races under concurrent requests.
        self._cache_lock = threading.Lock()

    @property
    def using_index(self) -> bool:
        return self._index_count > 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def list_sections(self) -> list[str]:
        return sorted(_SECTION_REGISTRY.keys())

    def get_content(self, section_key: str, force_live: bool = False) -> str:
        """
        Return the full content for a section key.

        Uses the SQLite index (fast path). Falls back to live scraping for
        sections missing from the index. Set force_live=True to always scrape.
        """
        if section_key not in _SECTION_REGISTRY:
            raise ValueError(
                f"Unknown section key: '{section_key}'. "
                "Use list_doc_sections to see available sections."
            )

        if not force_live:
            db = _get_db()
            if db:
                try:
                    row = db.execute(
                        "SELECT content FROM doc_sections WHERE section_key = ?",
                        (section_key,),
                    ).fetchone()
                    if row and row[0]:
                        return row[0]
                except Exception as exc:
                    logger.debug("SQLite lookup failed for section '%s': %s", section_key, exc)

            cached = self._live_cache.get(section_key)
            if cached is not None:
                content, cached_at = cached
                if time.time() - cached_at < config.docs_cache_ttl_seconds:
                    return content

        content = _live_fetch(section_key)
        with self._cache_lock:
            self._live_cache[section_key] = (content, time.time())
        return content

    def search(self, keyword: str) -> str:
        """
        Search across all documentation. Uses SQLite FTS5 when the index is available.
        Falls back to searching only live-cached sections when the index is absent.
        """
        lower = keyword.lower()
        db = _get_db()
        if db and self._index_count > 0:
            return self._fts_search(db, keyword)
        return self._cache_search(lower)

    # ------------------------------------------------------------------
    # SQLite FTS5 search
    # ------------------------------------------------------------------

    def _fts_search(self, db: sqlite3.Connection, keyword: str) -> str:
        use_snippet = True
        try:
            rows = db.execute(
                """
                SELECT
                    s.section_key,
                    s.title,
                    snippet(doc_fts, 2, '[', ']', '...', 30) AS snip
                FROM doc_fts
                JOIN doc_sections s ON s.rowid = doc_fts.rowid
                WHERE doc_fts MATCH ?
                ORDER BY rank
                LIMIT 10
                """,
                (keyword,),
            ).fetchall()
        except sqlite3.OperationalError:
            # FTS5 unavailable (e.g. SQLite built without FTS5) — fall back to LIKE
            use_snippet = False
            rows = db.execute(
                "SELECT section_key, title, content FROM doc_sections "
                "WHERE content LIKE ? LIMIT 10",
                (f"%{keyword}%",),
            ).fetchall()

        if not rows:
            return (
                f'No results found for "{keyword}" in the indexed documentation.\n'
                "Try a different keyword or use get_section_content with a specific section key."
            )

        results = []
        for row in rows:
            key   = row[0]
            title = row[1]
            raw   = row[2] if len(row) > 2 else ""
            # FTS5 already returns a pre-computed snippet; LIKE returns full content
            snip = raw if use_snippet else _snippet(raw, keyword.lower())
            header = f"## Section: {key}" + (f" — {title}" if title else "")
            results.append(f"{header}\n{snip}")

        return (
            f'Found {len(results)} section(s) matching "{keyword}":\n\n'
            + "\n\n".join(results)
        )

    # ------------------------------------------------------------------
    # Fallback: search only in-memory cached sections (no index)
    # ------------------------------------------------------------------

    def _cache_search(self, lower: str) -> str:
        results: list[str] = []
        for key in _SECTION_REGISTRY:
            if key not in self._live_cache:
                continue
            content, _ = self._live_cache[key]
            if lower in content.lower():
                snip = _snippet(content, lower)
                results.append(f"## Section: {key}\n{snip}")
            if len(results) >= 10:
                break

        if not results:
            return (
                f'No cached results for "{lower}". '
                "Run scripts/build_index.py to build the search index, "
                "or use get_section_content to fetch specific sections."
            )
        return (
            f'Found {len(results)} cached section(s) matching "{lower}":\n\n'
            + "\n\n".join(results)
        )


# Module-level singleton
doc_service = DocService()
