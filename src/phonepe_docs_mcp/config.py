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
Configuration for the docs MCP.

Optional env var:
  PHONEPE_DOCS_CACHE_TTL_SECONDS – how long live-scraped pages are cached in memory
                                   (seconds, default 3600). Non-integer values are
                                   silently ignored and the default is used.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _get_cache_ttl() -> int:
    try:
        return int(os.getenv("PHONEPE_DOCS_CACHE_TTL_SECONDS", "3600"))
    except (ValueError, TypeError):
        return 3600


@dataclass(frozen=True)
class DocsConfig:
    docs_cache_ttl_seconds: int = field(default_factory=_get_cache_ttl)


# Module-level singleton
config = DocsConfig()
