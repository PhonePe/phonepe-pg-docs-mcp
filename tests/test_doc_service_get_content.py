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

"""Tests for DocService.get_content() — cache hit/miss/TTL and force_live."""

from __future__ import annotations

import sys
import time
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import phonepe_docs_mcp.services.doc_service as ds_mod
from phonepe_docs_mcp.services.doc_service import DocService

REGISTRY = {
    "overview":    "/docs/overview",
    "refund-api":  "/docs/refund",
    "not-indexed": "/docs/not-indexed",
}


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


class TestDBHit:
    def test_returns_content_from_index(self, svc, mem_db):
        with patch.object(ds_mod, "_get_db", return_value=mem_db):
            content = svc.get_content("overview")
        assert "PhonePe" in content or "UPI" in content

    def test_no_live_fetch_when_db_has_content(self, svc, mem_db):
        with patch.object(ds_mod, "_get_db", return_value=mem_db), \
             patch.object(ds_mod, "_live_fetch") as mock_fetch:
            svc.get_content("overview")
        mock_fetch.assert_not_called()

    def test_null_content_falls_through_to_live(self, svc, mem_db):
        with patch.object(ds_mod, "_get_db", return_value=mem_db), \
             patch.object(ds_mod, "_live_fetch", return_value="live content") as mock_fetch:
            content = svc.get_content("not-indexed")
        mock_fetch.assert_called_once_with("not-indexed")
        assert content == "live content"


class TestCacheHitMiss:
    def test_cache_miss_calls_live_fetch(self, svc):
        with patch.object(ds_mod, "_get_db", return_value=None), \
             patch.object(ds_mod, "_live_fetch", return_value="scraped") as mock_fetch:
            content = svc.get_content("overview")
        assert content == "scraped"
        mock_fetch.assert_called_once_with("overview")
        assert "overview" in svc._live_cache

    def test_cache_hit_no_refetch(self, svc):
        svc._live_cache["overview"] = ("cached", time.time())
        with patch.object(ds_mod, "_get_db", return_value=None), \
             patch.object(ds_mod, "_live_fetch") as mock_fetch:
            content = svc.get_content("overview")
        assert content == "cached"
        mock_fetch.assert_not_called()

    def test_expired_cache_refetches(self, svc):
        svc._live_cache["overview"] = ("stale", time.time() - 99999)
        with patch.object(ds_mod, "_get_db", return_value=None), \
             patch.object(ds_mod, "_live_fetch", return_value="fresh") as mock_fetch:
            content = svc.get_content("overview")
        assert content == "fresh"
        mock_fetch.assert_called_once()
        cached_content, cached_at = svc._live_cache["overview"]
        assert cached_content == "fresh"
        assert time.time() - cached_at < 5


class TestForceLive:
    def test_skips_db(self, svc, mem_db):
        with patch.object(ds_mod, "_get_db", return_value=mem_db), \
             patch.object(ds_mod, "_live_fetch", return_value="force-live") as mock_fetch:
            content = svc.get_content("overview", force_live=True)
        assert content == "force-live"
        mock_fetch.assert_called_once_with("overview")

    def test_skips_cache(self, svc):
        svc._live_cache["overview"] = ("old", time.time())
        with patch.object(ds_mod, "_get_db", return_value=None), \
             patch.object(ds_mod, "_live_fetch", return_value="new-live") as mock_fetch:
            content = svc.get_content("overview", force_live=True)
        assert content == "new-live"
        mock_fetch.assert_called_once()


class TestUnknownKey:
    def test_raises_value_error(self, svc, mem_db):
        with patch.object(ds_mod, "_get_db", return_value=mem_db):
            with pytest.raises(ValueError, match="Unknown section key"):
                svc.get_content("does-not-exist")
