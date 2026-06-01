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
Tests for KnowledgeBaseService.answer_question() — FAQ scoring with
word-boundary matching (post-fix for substring false-positive review comment).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import phonepe_docs_mcp.services.kb_service as kb_mod
from phonepe_docs_mcp.services.kb_service import KnowledgeBaseService


class TestAnswerQuestionFAQScoring:
    def _service(self, kb: dict) -> KnowledgeBaseService:
        import phonepe_docs_mcp.services.kb_service as m
        self._orig = m._KB
        m._KB = kb
        return KnowledgeBaseService.__new__(KnowledgeBaseService)

    def teardown_method(self, _):
        import phonepe_docs_mcp.services.kb_service as m
        if hasattr(self, "_orig"):
            m._KB = self._orig

    def test_keyword_match_returns_answer(self, synthetic_kb):
        svc = self._service(synthetic_kb)
        result = svc.answer_question("Tell me about international payments")
        assert "INR" in result

    def test_autopay_keyword_match(self, synthetic_kb):
        svc = self._service(synthetic_kb)
        result = svc.answer_question("How do I configure autopay for recurring billing?")
        assert "SUBSCRIPTION_CHECKOUT_SETUP" in result or "AutoPay" in result

    def test_unrelated_question_falls_through(self, synthetic_kb):
        svc = self._service(synthetic_kb)
        result = svc.answer_question("xyz irrelevant blah blah")
        assert "INR-only" not in result
        assert "SUBSCRIPTION_CHECKOUT_SETUP" not in result

    def test_short_words_not_scored(self, synthetic_kb):
        """Words ≤ 3 chars don't contribute to score."""
        svc = self._service(synthetic_kb)
        result = svc.answer_question("is in the of")
        assert "INR" not in result

    def test_word_boundary_prevents_false_positive(self, synthetic_kb):
        """'ment' is a substring of 'payment' but must NOT match as a word.
        With the re.search word-boundary fix, this should score 0."""
        svc = self._service(synthetic_kb)
        result = svc.answer_question("ment tion ness")
        assert "INR-only" not in result
        assert "SUBSCRIPTION_CHECKOUT_SETUP" not in result

    def test_false_positive_protection_with_empty_kb(self):
        svc = KnowledgeBaseService.__new__(KnowledgeBaseService)
        import phonepe_docs_mcp.services.kb_service as m
        orig = m._KB
        m._KB = {"faqs": [], "api_quick_reference": []}
        try:
            assert svc.answer_question("international payments") == ""
        finally:
            m._KB = orig

    def test_multi_keyword_picks_best_faq(self, synthetic_kb):
        svc = self._service(synthetic_kb)
        result = svc.answer_question("How does autopay mandate work?")
        assert "SUBSCRIPTION_CHECKOUT_SETUP" in result or "AutoPay" in result
