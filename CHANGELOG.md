# Changelog — phonepe-pg-docs-mcp

## [1.0.0] — 2025-05-12

### Added
- Initial release: documentation-only MCP server
- 244+ doc sections covering Standard Checkout, Custom Checkout, AutoPay, Payment Links, Mobile SDKs, Backend SDKs, Settlement, Chargeback, PG Health Check, TSP, Split Settlement, Native OTP, and more
- Documentation tools: `list_doc_sections`, `get_section_content`, `search_docs`, `get_api_endpoints`, `get_prerequisites`, `get_environments`
- Knowledge base tools: `ask_knowledge_base`, `list_products`, `get_feature_support`, `get_error_code_info`
- TTL-based in-memory cache for scraped pages (default 1 hour)
- Configurable via `docs_registry.yml` — add new sections without code changes
