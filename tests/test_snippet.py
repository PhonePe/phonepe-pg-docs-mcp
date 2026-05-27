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

"""Tests for _snippet() helper in doc_service.py."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from phonepe_docs_mcp.services.doc_service import _snippet


class TestSnippet:
    def test_keyword_in_middle(self):
        content = "A" * 200 + "refund" + "B" * 400
        snip = _snippet(content, "refund")
        assert "refund" in snip
        assert snip.startswith("...") and snip.endswith("...")

    def test_keyword_near_start(self):
        content = "refund happens here. " + "X" * 500
        snip = _snippet(content, "refund")
        assert "refund" in snip

    def test_keyword_near_end(self):
        content = "X" * 500 + " authorization_failed"
        snip = _snippet(content, "authorization_failed")
        assert "authorization_failed" in snip

    def test_keyword_not_found_returns_empty(self):
        assert _snippet("Some content without the term", "nonexistent") == ""

    def test_entire_content_is_keyword(self):
        assert "refund" in _snippet("refund", "refund")

    def test_keyword_case_insensitive_search(self):
        """_snippet uses content.lower().find(keyword) so lowercase keyword
        finds uppercase text; the returned slice is from original content."""
        content = "The REFUND process is simple."
        snip = _snippet(content, "refund")
        assert "REFUND" in snip

    def test_truly_absent_keyword_returns_empty(self):
        assert _snippet("The REFUND process is simple.", "mandate") == ""

    def test_snippet_length_bounded(self):
        content = "A" * 300 + "mandate" + "B" * 600
        snip = _snippet(content, "mandate")
        inner = snip.strip(".")
        assert len(inner) <= 150 + len("mandate") + 300 + 10

    def test_empty_content(self):
        assert _snippet("", "anything") == ""
