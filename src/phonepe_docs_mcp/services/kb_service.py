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
PhonePe PG Knowledge Base Service.

Loads knowledge_base.yml at startup and provides fast, structured answers
to product/feature existence questions, FAQs, error codes, and API quick
reference lookups — all without network calls.
"""

from __future__ import annotations

import logging
import re
from typing import Any

import yaml

logger = logging.getLogger(__name__)

from ._paths import KB_YAML as _KB_FILE


def _load_kb() -> dict[str, Any]:
    if not _KB_FILE.exists():
        return {}
    with _KB_FILE.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


_KB: dict[str, Any] = _load_kb()


class KnowledgeBaseService:
    """Answers PhonePe PG product/feature/API questions from the knowledge base."""

    def list_products(self) -> str:
        products = _KB.get("products", {})
        if not products:
            return "Knowledge base not loaded. Ensure knowledge_base.yml is present."

        lines = ["## PhonePe PG — Products in Production\n"]
        for pid, info in products.items():
            name = info.get("name", pid)
            status = info.get("status", "unknown")
            perm = info.get("permission_required", False)
            perm_name = info.get("permission_name", "")
            desc = (info.get("description") or "").strip().split("\n")[0][:120]
            perm_label = f"  *(requires: {perm_name})*" if perm else "  *(available by default)*"
            lines.append(f"### {name}{perm_label}")
            lines.append(f"Status: {status.upper()}")
            lines.append(desc)
            lines.append("")

        return "\n".join(lines)

    def get_feature_support(self, feature: str) -> str:
        feature_matrix = _KB.get("feature_matrix", {})
        if not feature_matrix:
            return "Feature matrix not available in knowledge base."

        lower = feature.lower().replace(" ", "_").replace("-", "_")
        if lower in feature_matrix:
            return self._format_feature(lower, feature_matrix[lower])

        matches = [k for k in feature_matrix if lower in k or k in lower]
        if len(matches) == 1:
            return self._format_feature(matches[0], feature_matrix[matches[0]])
        if len(matches) > 1:
            results = [self._format_feature(m, feature_matrix[m]) for m in matches]
            return f"Found {len(matches)} matching features:\n\n" + "\n\n---\n\n".join(results)

        keyword_results = []
        for key, val in feature_matrix.items():
            notes = str(val.get("notes", "") if isinstance(val, dict) else val)
            if lower in notes.lower() or lower in key.lower():
                keyword_results.append(self._format_feature(key, val))
        if keyword_results:
            return "\n\n---\n\n".join(keyword_results[:3])

        available = ", ".join(feature_matrix.keys())
        return (
            f"Feature '{feature}' not found in the knowledge base.\n"
            f"Available feature keys: {available}"
        )

    @staticmethod
    def _format_feature(key: str, val: Any) -> str:
        name = key.replace("_", " ").title()
        if isinstance(val, dict):
            supported = val.get("supported")
            values = val.get("values")
            notes = val.get("notes", "")
            lines = [f"## {name}"]
            if supported is not None:
                lines.append(f"**Supported:** {'Yes' if supported else 'No'}")
            if values:
                lines.append(f"**Values:** {', '.join(str(v) for v in values)}")
            if notes:
                lines.append(f"\n{notes.strip()}")
            return "\n".join(lines)
        return f"## {name}\n{val}"

    def answer_question(self, question: str) -> str:
        """
        Search FAQs and API quick reference for an answer.
        Returns empty string if no match found (caller falls through to search_docs).
        """
        faqs = _KB.get("faqs", [])
        q_lower = question.lower()

        if faqs:
            best_score = 0
            best_faq: dict | None = None
            for faq in faqs:
                score = 0
                faq_q = faq.get("q", "").lower()
                keywords = [k.lower() for k in faq.get("keywords", [])]
                for word in q_lower.split():
                    if len(word) > 3 and re.search(r'\b' + re.escape(word) + r'\b', faq_q):
                        score += 2
                for kw in keywords:
                    if kw in q_lower:
                        score += 3
                if score > best_score:
                    best_score = score
                    best_faq = faq
            if best_faq and best_score >= 3:
                q_text = best_faq.get("q", "")
                a_text = (best_faq.get("a") or "").strip()
                return f"**Q: {q_text}**\n\n{a_text}"

        return self._search_api_quick_ref(q_lower)

    def _search_api_quick_ref(self, q_lower: str) -> str:
        refs = _KB.get("api_quick_reference", [])
        matches = [r for r in refs if any(w in r.get("task", "").lower() for w in q_lower.split() if len(w) > 3)]
        if not matches:
            return ""
        lines = ["## Matching APIs from Quick Reference\n"]
        for ref in matches[:5]:
            lines.append(f"**{ref.get('task', '')}**")
            lines.append(f"`{ref.get('method', '')} {ref.get('endpoint', '')}`")
            doc = ref.get("doc_section", "")
            if doc:
                lines.append(f"Doc: get_section_content('{doc}')")
            lines.append("")
        return "\n".join(lines)

    def get_error_code_info(self, error_code: str) -> str:
        codes = _KB.get("error_codes", {})
        if not codes:
            return "Error code reference not available in knowledge base."

        code_upper = error_code.upper().strip()
        if code_upper in codes:
            info = codes[code_upper]
            http = info.get("http_status", "")
            cause = (info.get("cause") or "").strip()
            resolution = (info.get("resolution") or "").strip()
            return (
                f"## Error: {code_upper}\n\n"
                f"**HTTP Status:** {http}\n\n"
                f"**Cause:** {cause}\n\n"
                f"**Resolution:** {resolution}"
            )

        matches = [k for k in codes if error_code.upper() in k or k in error_code.upper()]
        if matches:
            return "\n\n---\n\n".join(self.get_error_code_info(m) for m in matches)

        return (
            f"Error code '{error_code}' not found.\n"
            f"Known codes: {', '.join(codes.keys())}"
        )

kb_service = KnowledgeBaseService()

