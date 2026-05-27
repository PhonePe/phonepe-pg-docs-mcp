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
Resolve paths to bundled knowledge files.

Works correctly in all scenarios:
  1. Editable install (pip install -e .)       → reads from src/phonepe_docs_mcp/knowledge/
  2. Wheel install (pip install / uvx)         → reads from installed package directory
  3. Direct development run                    → same as editable install
"""

from __future__ import annotations

from pathlib import Path

# Both doc_index.db and knowledge_base.yml are bundled inside the package
# at phonepe_docs_mcp/knowledge/
_KNOWLEDGE_DIR = Path(__file__).parent.parent / "knowledge"

INDEX_DB   = _KNOWLEDGE_DIR / "doc_index.db"
KB_YAML    = _KNOWLEDGE_DIR / "knowledge_base.yml"

# docs_registry.yml stays at project root for easy editing;
# fall back to a copy bundled in the package if not found at root
_PROJECT_ROOT  = Path(__file__).parent.parent.parent.parent
REGISTRY_FILE  = _PROJECT_ROOT / "docs_registry.yml"
if not REGISTRY_FILE.exists():
    # Installed package — use bundled copy
    REGISTRY_FILE = _KNOWLEDGE_DIR / "docs_registry.yml"
