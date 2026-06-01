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

"""Tests for KnowledgeBaseService.get_feature_support() — normalisation and lookup."""

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


class TestFeatureNormalisation:
    def test_underscore(self, svc):
        assert "INR" in svc.get_feature_support("international_payments")

    def test_hyphen(self, svc):
        assert "INR" in svc.get_feature_support("international-payments")

    def test_space(self, svc):
        assert "INR" in svc.get_feature_support("international payments")

    def test_mixed(self, svc):
        result = svc.get_feature_support("card-networks")
        assert "VISA" in result or "card_networks" in result.lower()


class TestFeatureExactMatch:
    def test_supported_false(self, svc):
        assert "No" in svc.get_feature_support("international_payments")

    def test_supported_true(self, svc):
        assert "Yes" in svc.get_feature_support("refunds")

    def test_values_listed(self, svc):
        result = svc.get_feature_support("card_networks")
        assert "VISA" in result and "RUPAY" in result


class TestFeaturePartialMatch:
    def test_substring_match(self, svc):
        result = svc.get_feature_support("card")
        assert "VISA" in result or "card" in result.lower()


class TestFeatureNotFound:
    def test_unknown_returns_not_found(self, svc):
        assert "not found" in svc.get_feature_support("quantum_mode").lower()

    def test_empty_matrix(self):
        svc = KnowledgeBaseService()
        orig = kb_mod._KB
        kb_mod._KB = {"feature_matrix": {}}
        try:
            assert "not available" in svc.get_feature_support("refunds").lower()
        finally:
            kb_mod._KB = orig
