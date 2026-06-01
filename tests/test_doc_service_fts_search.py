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

"""Tests for DocService._fts_search() — FTS5 path and LIKE fallback."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import phonepe_docs_mcp.services.doc_service as ds_mod
from phonepe_docs_mcp.services.doc_service import DocService

REGISTRY = {"overview": "/", "refund-api": "/refund", "autopay": "/autopay"}


@pytest.fixture(autouse=True)
def patch_registry():
    with patch.object(ds_mod, "_SECTION_REGISTRY", REGISTRY):
        yield


@pytest.fixture()
def svc(mem_db):
    with patch.object(ds_mod, "_get_db", return_value=mem_db):
        service = DocService()
    service._index_count = 3
    return service


class TestFTSPath:
    def test_fts5_hit(self, svc, mem_db):
        result = svc._fts_search(mem_db, "refund")
        assert "refund" in result.lower()

    def test_fts5_no_results(self, svc, mem_db):
        result = svc._fts_search(mem_db, "completely_unknown_xyz_9999")
        assert "No results found" in result

    def test_result_bounded_to_10(self, svc):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.executescript(
            "CREATE TABLE doc_sections (section_key TEXT, title TEXT, content TEXT);"
            "CREATE VIRTUAL TABLE doc_fts USING fts5("
            "  section_key, title, content,"
            "  content='doc_sections', content_rowid='rowid'"
            ");"
        )
        for i in range(15):
            conn.execute(
                "INSERT INTO doc_sections VALUES (?, ?, ?)",
                (f"key-{i}", f"Title {i}", f"PhonePe refund content {i}"),
            )
        conn.execute(
            "INSERT INTO doc_fts(rowid, section_key, title, content) "
            "SELECT rowid, section_key, title, content FROM doc_sections"
        )
        conn.commit()
        result = svc._fts_search(conn, "refund")
        conn.close()
        assert result.count("## Section:") <= 10


class TestLIKEFallbackPath:
    """sqlite3.Connection.execute is read-only in CPython ≥ 3.12 so we use
    a wrapper shim to simulate FTS5 being unavailable."""

    @staticmethod
    def _broken_fts5(real_conn):
        class _Wrapper:
            def __init__(self, c):
                self._c = c
                self.row_factory = c.row_factory

            def execute(self, sql, params=()):
                if "doc_fts" in sql and "MATCH" in sql:
                    raise sqlite3.OperationalError("no such module: fts5")
                return self._c.execute(sql, params)

            def __getattr__(self, n):
                return getattr(self._c, n)

        return _Wrapper(real_conn)

    def test_like_fallback_runs(self, svc, mem_db):
        result = svc._fts_search(self._broken_fts5(mem_db), "refund")
        assert "refund" in result.lower()

    def test_like_fallback_uses_snippet(self, svc, mem_db):
        """BUG 2 fix: LIKE path must call _snippet(), not return raw content."""
        with patch.object(ds_mod, "_snippet", wraps=ds_mod._snippet) as spy:
            svc._fts_search(self._broken_fts5(mem_db), "refund")
        spy.assert_called()

    def test_like_fallback_no_results(self, svc, mem_db):
        result = svc._fts_search(self._broken_fts5(mem_db), "completely_unknown_xyz_9999")
        assert "No results found" in result
