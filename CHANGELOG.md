# Changelog — phonepe-pg-docs-mcp

## [1.0.1] — 2026-06-09

### Fixed
- Filter bare newline / whitespace-only lines from stdin before the MCP
  JSON-RPC parser sees them, eliminating `Invalid JSON: EOF` errors sent
  by some clients (Claude Desktop, VS Code, etc.) as keepalive lines
- Corrected `uvx` invocation in README and mcp-config examples from
  `uvx phonepe-pg-docs-mcp` to `uvx --from phonepe-pg-docs-mcp phonepe-pg-docs`

### Changed
- Added `~/.copilot/mcp-config.json` as an alternate config path for GitHub Copilot
- Fixed dev install command in README from `.[dev]` to `.[test]`

---

## [1.0.0] — 2025-05-12

### Added
- Initial release: documentation-only MCP server
- 244+ doc sections covering Standard Checkout, Custom Checkout, AutoPay, Payment Links, Mobile SDKs, Backend SDKs, Settlement, Chargeback, PG Health Check, TSP, Split Settlement, Native OTP, and more
- Documentation tools: `list_doc_sections`, `get_section_content`, `search_docs`, `get_api_endpoints`, `get_prerequisites`, `get_environments`
- Knowledge base tools: `ask_knowledge_base`, `list_products`, `get_feature_support`, `get_error_code_info`
- TTL-based in-memory cache for scraped pages (default 1 hour)
- Configurable via `docs_registry.yml` — add new sections without code changes
