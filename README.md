# phonepe-pg-docs-mcp

> **PhonePe Payment Gateway — Documentation & Knowledge Base MCP**

[![PyPI version](https://img.shields.io/pypi/v/phonepe-pg-docs-mcp)](https://pypi.org/project/phonepe-pg-docs-mcp/)
[![Python](https://img.shields.io/pypi/pyversions/phonepe-pg-docs-mcp)](https://pypi.org/project/phonepe-pg-docs-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io/) server published by **PhonePe** that gives any AI agent — Claude, GPT, Cursor, Copilot, Windsurf — instant access to PhonePe Payment Gateway developer documentation and a curated knowledge base.

Integrate PhonePe PG faster by letting your AI coding assistant answer questions directly from the official docs, without leaving your IDE.

> **No PhonePe credentials required.** This MCP is entirely read-only.  
> For live payment API calls (initiate payments, refunds, payment links), see the companion package [`phonepe-pg-payments-mcp`](https://pypi.org/project/phonepe-pg-payments-mcp/).

---

## Why use this?

When integrating PhonePe PG, developers commonly need to:

- Look up which API to call for a specific action
- Understand the request/response schema for an endpoint
- Check what order states exist and what each means
- Debug error codes like `AUTHORIZATION_FAILED`
- Find out if PhonePe supports a feature (recurring payments, international, EMI, etc.)
- Compare Standard Checkout vs Custom Checkout vs Payment Links

This MCP lets your AI agent answer all of these questions instantly — from a pre-indexed, always-up-to-date snapshot of the official developer docs — so you can stay in your editor and keep coding.

---

## How it works

```
Your question to the AI agent
          │
          ▼
┌──────────────────────────────────┐
│  Tier 1 · knowledge_base.yml     │  ~0 ms   Curated answers: products,
│  30 KB YAML, loaded at startup   │ ───────▶  features, FAQs, error codes
└──────────────────────────────────┘
          │ not found
          ▼
┌──────────────────────────────────┐
│  Tier 2 · SQLite FTS5 index      │  ~2 ms   Full-text search across
│  doc_index.db, 2.4 MB on disk    │ ───────▶  241 developer doc sections
└──────────────────────────────────┘
          │ section not yet indexed
          ▼
┌──────────────────────────────────┐
│  Tier 3 · Live web scraping      │  ~1–2 s  Fetches from
│  developer.phonepe.com           │ ───────▶  developer.phonepe.com
└──────────────────────────────────┘
```

The SQLite index is **pre-built and shipped inside the PyPI wheel**. Every `pip install` or `uvx` run gives you the latest indexed docs at sub-millisecond search speed — no network calls needed for search.

---

## Available tools (10 total)

### 🧠 Knowledge base tools — instant, no network

| Tool | What it answers |
|------|-----------------|
| `ask_knowledge_base` | Any product / feature / API / error question in natural language |
| `list_products` | All live PhonePe PG products and which ones require special permission |
| `get_feature_support` | "Does PhonePe support X?" — refunds, recurring, international, EMI, etc. |
| `get_error_code_info` | HTTP status, cause, and resolution for any PhonePe error code |

### 📚 Documentation tools — SQLite FTS5 backed

| Tool | Description |
|------|-------------|
| `search_docs` | Keyword search across all 241 doc sections (~2 ms) |
| `list_doc_sections` | Browse the full list of available documentation sections |
| `get_section_content` | Fetch the full content of any specific doc section |
| `get_api_endpoints` | Complete API endpoint reference table |
| `get_prerequisites` | Setup checklist per integration type |
| `get_environments` | Sandbox and production base URLs |

---

## Set up in your AI client

Pick your client and add the following config. Restart the client after saving.

### Claude Desktop

**Config file:**
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "phonepe-pg-docs": {
      "command": "uvx",
      "args": ["--from", "phonepe-pg-docs-mcp", "phonepe-pg-docs"]
    }
  }
}
```

### Cursor

**Config file:** `~/.cursor/mcp.json` (global) or `.cursor/mcp.json` in your project

```json
{
  "mcpServers": {
    "phonepe-pg-docs": {
      "command": "uvx",
      "args": ["--from", "phonepe-pg-docs-mcp", "phonepe-pg-docs"]
    }
  }
}
```

### GitHub Copilot (VS Code)

**Config file (workspace):** `.vscode/mcp.json`  
**Config file (user-level):** `~/.copilot/mcp-config.json`

```json
{
  "servers": {
    "phonepe-pg-docs": {
      "type": "stdio",
      "command": "uvx",
      "args": ["--from", "phonepe-pg-docs-mcp", "phonepe-pg-docs"]
    }
  }
}
```

### Windsurf

**Config file:** `~/.codeium/windsurf/mcp_config.json`

```json
{
  "mcpServers": {
    "phonepe-pg-docs": {
      "command": "uvx",
      "args": ["--from", "phonepe-pg-docs-mcp", "phonepe-pg-docs"]
    }
  }
}
```

### Using `pip` instead of `uvx`

Replace the `command`/`args` block in any config above with:

```json
"command": "phonepe-pg-docs",
"args": []
```

---

## Installation

**Requirements:** Python 3.10 or higher. No API keys needed.

### Using `uvx`

```bash
uvx --from phonepe-pg-docs-mcp phonepe-pg-docs
```

### Using `pip`

```bash
pip install phonepe-pg-docs-mcp
phonepe-pg-docs
```

---

## Example conversations

Once configured, talk to your AI agent naturally:

```
You: "Does PhonePe support recurring payments?"
MCP: ask_knowledge_base → Yes. UPI AutoPay and eNACH are supported.
     Requires the AutoPay permission to be enabled by PhonePe...

You: "What API do I call to generate a UPI QR for payment?"
MCP: ask_knowledge_base → POST /payments/v2/pay with paymentFlow.type = UPI_QR
     Doc: get_section_content('custom-checkout-v2/pay/upi-qr')

You: "Show me the full Custom Checkout UPI Intent integration steps"
MCP: get_section_content('custom-checkout-v2/pay/upi-intent') → full guide

You: "Find everything about webhook verification"
MCP: search_docs('webhook') → 10 matching sections in 2 ms

You: "What does AUTHORIZATION_FAILED mean?"
MCP: get_error_code_info → HTTP 401, expired token, re-fetch via /v1/oauth/token

You: "What are all the states a PhonePe payment order can be in?"
MCP: ask_knowledge_base → PENDING, COMPLETED, FAILED, CANCELLED + descriptions

You: "Which PhonePe products need special permission to use?"
MCP: list_products → Custom Checkout, AutoPay, Payment Links (each individually gated)
```

---

## Configuration reference

| Environment variable | Default | Description |
|----------------------|---------|-------------|
| `PHONEPE_DOCS_CACHE_TTL_SECONDS` | `3600` | Cache TTL for live-fetched pages (Tier 3 fallback only) |

Set via a `.env` file in your working directory or export the variable. Not required for standard use.

---

## Contributing

Contributions to PhonePe PG Docs MCP are welcome! Here's how you can contribute:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Please ensure your code follows the project's coding standards and includes appropriate tests.

### Adding or fixing documentation sections

The full list of indexed pages is in [`docs_registry.yml`](./docs_registry.yml). To add a new page:

1. Add an entry under `sections.public` or `sections.additional`:
   ```yaml
   my-new-section: /payment-gateway/path/to/page
   ```
2. Rebuild the local index:
   ```bash
   pip install httpx pyyaml beautifulsoup4
   python scripts/build_index.py
   ```
3. Verify with a search: `search_docs("your new topic")`
4. Open a pull request

### Updating the curated knowledge base

Product descriptions, feature flags, FAQs, and error code explanations live in  
`src/phonepe_docs_mcp/knowledge/knowledge_base.yml`. Edit that file directly — no code changes needed.

### Running locally (development)

```bash
git clone https://github.com/PhonePe/phonepe-pg-docs-mcp.git
cd phonepe-pg-docs-mcp
pip install -e ".[test]"

# Build the doc index (required once before first run)
python scripts/build_index.py

# Run tests
pytest

# Start the MCP server
phonepe-pg-docs
```

---

## Releasing a new version (maintainers)

1. Bump `version` in `pyproject.toml`
2. Add a changelog entry in `CHANGELOG.md`
3. Merge to `main`
4. Trigger the **Manual Release to PyPI** GitHub Actions workflow

The CI pipeline automatically:
1. Runs `python scripts/build_index.py` — re-indexes all 241 doc sections with the latest content
2. Bundles the fresh `doc_index.db` inside the wheel
3. Publishes to PyPI via `twine`

Every `pip install phonepe-pg-docs-mcp` always delivers the latest pre-indexed documentation snapshot.

---

## Companion MCP — live payment API calls

To actually initiate payments, create payment links, process refunds, or poll order status from your AI agent:

```bash
uvx phonepe-pg-payments-mcp
```

Requires: `PHONEPE_CLIENT_ID`, `PHONEPE_CLIENT_SECRET`, `PHONEPE_CLIENT_VERSION`  
PyPI: [phonepe-pg-payments-mcp](https://pypi.org/project/phonepe-pg-payments-mcp/)

---

## Official documentation

| Resource | Link |
|----------|------|
| PhonePe PG Developer Portal | https://developer.phonepe.com |
| Standard Checkout | https://developer.phonepe.com/phonepe-payment-gateway/pg-v2-standard-checkout-integration |
| Custom Checkout | https://developer.phonepe.com/payment-gateway-custom-checkout/custom-api-integration/introduction-api-integration-custom |
| AutoPay / Recurring | https://developer.phonepe.com/payment-gateway/autopay/api-integration/introduction |
| Payment Links | https://developer.phonepe.com/payment-gateway/payment-links/introduction |
| Chargeback APIs | https://developer.phonepe.com/chargeback |

---

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

```
Copyright 2025 PhonePe Private Limited

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```

---

## Support

- **Bug reports / feature requests:** Open an issue on GitHub
- **PhonePe PG account or enablement questions:** Contact your PhonePe account manager or write to pg-developer@phonepe.com
