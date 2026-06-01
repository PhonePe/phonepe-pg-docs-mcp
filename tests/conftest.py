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
Shared pytest fixtures for phonepe-pg-docs-mcp tests.
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Generator

import pytest
import yaml

REPO_ROOT = Path(__file__).parent.parent
SRC_ROOT  = REPO_ROOT / "src"
KB_YAML   = SRC_ROOT / "phonepe_docs_mcp" / "knowledge" / "knowledge_base.yml"


@pytest.fixture()
def mem_db() -> Generator[sqlite3.Connection, None, None]:
    """In-memory SQLite DB with doc_sections + FTS5 virtual table."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(
        "CREATE TABLE doc_sections ("
        "  section_key TEXT PRIMARY KEY, title TEXT, content TEXT"
        ");"
        "CREATE VIRTUAL TABLE doc_fts USING fts5("
        "  section_key, title, content,"
        "  content='doc_sections', content_rowid='rowid'"
        ");"
    )
    rows = [
        ("overview",    "PhonePe Overview",
         "PhonePe Payment Gateway supports UPI, Cards, and Net Banking."),
        ("refund-api",  "Refund API",
         "Use the refund endpoint to initiate a full or partial refund. "
         "The AUTHORIZATION_FAILED error means your token has expired."),
        ("autopay",     "AutoPay / Recurring",
         "AutoPay lets merchants set up recurring mandates via UPI. "
         "Mandate types: FIXED or VARIABLE. Frequency: MONTHLY, DAILY etc."),
        ("not-indexed", "Missing from index", None),
    ]
    conn.executemany("INSERT INTO doc_sections VALUES (?, ?, ?)", rows)
    conn.executemany(
        "INSERT INTO doc_fts(rowid, section_key, title, content) "
        "SELECT rowid, section_key, title, content "
        "FROM doc_sections WHERE section_key = ?",
        [(r[0],) for r in rows if r[2] is not None],
    )
    conn.commit()
    yield conn
    conn.close()


@pytest.fixture()
def synthetic_kb() -> dict:
    """Minimal in-memory knowledge base — no file I/O needed."""
    return {
        "products": {
            "standard_checkout": {
                "name": "Standard Checkout",
                "status": "live",
                "permission_required": False,
                "description": "PhonePe-hosted payment page.",
            },
        },
        "feature_matrix": {
            "international_payments": {
                "supported": False,
                "notes": "PhonePe PG supports INR only.",
            },
            "refunds": {
                "supported": True,
                "notes": "Full and partial refunds supported.",
            },
            "card_networks": {
                "supported": True,
                "values": ["VISA", "MASTERCARD", "RUPAY"],
                "notes": "Cards supported via Custom Checkout.",
            },
        },
        "faqs": [
            {
                "id": "f1",
                "category": "general",
                "q": "Does PhonePe PG support international payments?",
                "keywords": ["international", "foreign", "global", "USD", "EUR"],
                "a": "No. PhonePe PG is INR-only.",
            },
            {
                "id": "f2",
                "category": "autopay",
                "q": "How do I set up AutoPay recurring payments?",
                "keywords": ["autopay", "recurring", "subscription", "mandate"],
                "a": "Use SUBSCRIPTION_CHECKOUT_SETUP for Standard Checkout AutoPay.",
            },
        ],
        "error_codes": {
            "AUTHORIZATION_FAILED": {
                "http_status": 401,
                "cause": "Expired or invalid OAuth token.",
                "resolution": "Re-fetch token via /v1/oauth/token and retry once.",
            },
            "BAD_REQUEST": {
                "http_status": 400,
                "cause": "Malformed request body.",
                "resolution": "Check all required fields.",
            },
        },
        "api_quick_reference": [
            {
                "task": "Create payment order",
                "method": "POST",
                "endpoint": "/checkout/v2/pay",
                "doc_section": "website/standard-checkout/create-payment",
            },
        ],
    }
