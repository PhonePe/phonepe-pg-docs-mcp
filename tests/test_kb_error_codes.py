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

"""Tests for KnowledgeBaseService error-code lookup."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import phonepe_docs_mcp.services.kb_service as kb_mod
from phonepe_docs_mcp.services.kb_service import KnowledgeBaseService


@pytest.fixture(autouse=True)
def patch_kb(synthetic_kb):
    orig = kb_mod._KB
    kb_mod._KB = synthetic_kb
    yield
    kb_mod._KB = orig


@pytest.fixture()
def svc():
    return KnowledgeBaseService()


class TestErrorCodeExactMatch:
    def test_authorization_failed(self, svc):
        result = svc.get_error_code_info("AUTHORIZATION_FAILED")
        assert "401" in result and "OAuth token" in result

    def test_bad_request(self, svc):
        result = svc.get_error_code_info("BAD_REQUEST")
        assert "400" in result

    def test_case_insensitive(self, svc):
        assert "401" in svc.get_error_code_info("authorization_failed")

    def test_strips_whitespace(self, svc):
        assert "401" in svc.get_error_code_info("  AUTHORIZATION_FAILED  ")


class TestErrorCodePartialMatch:
    def test_partial_suffix(self, svc):
        result = svc.get_error_code_info("FAILED")
        assert "AUTHORIZATION_FAILED" in result

    def test_partial_prefix(self, svc):
        result = svc.get_error_code_info("AUTHORIZATION")
        assert "AUTHORIZATION_FAILED" in result


class TestErrorCodeNotFound:
    def test_unknown_returns_not_found(self, svc):
        assert "not found" in svc.get_error_code_info("COMPLETELY_UNKNOWN").lower()

    def test_not_found_lists_known_codes(self, svc):
        result = svc.get_error_code_info("UNKNOWN_CODE")
        assert "AUTHORIZATION_FAILED" in result or "Known codes" in result

    def test_empty_kb(self):
        svc = KnowledgeBaseService()
        orig = kb_mod._KB
        kb_mod._KB = {}
        try:
            assert "not available" in svc.get_error_code_info("X").lower()
        finally:
            kb_mod._KB = orig
