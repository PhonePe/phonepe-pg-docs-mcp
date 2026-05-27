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
MCP tools that expose PhonePe PG developer documentation to AI agents.

No PhonePe credentials required — all tools are read-only documentation access.
"""

from __future__ import annotations

import logging

from mcp.server.fastmcp import FastMCP

from ..services.doc_service import doc_service

logger = logging.getLogger(__name__)


def register_doc_tools(mcp: FastMCP) -> None:
    """Register all documentation tools on the given FastMCP instance."""

    @mcp.tool()
    def list_doc_sections() -> str:
        """
        List all available PhonePe Payment Gateway documentation sections.

        Returns a list of section keys that can be used with other tools.
        Use this first to discover what documentation is available before
        fetching specific content.

        Sections are grouped by integration type:
          overview              - High-level overview
          website/...           - Website (Standard Checkout) integration
          autopay/...           - UPI AutoPay / recurring payments
          payment-links/...     - Payment Links
          plugins/...           - E-commerce plugins (WooCommerce, Shopify)
          sdk/backend-standard/ - Backend SDKs (Java, Python, Node.js, PHP)
          sdk/mobile-standard/  - Mobile SDKs (Android, iOS, Flutter, React Native, Ionic)
          custom-checkout-v2/   - Custom Checkout V2 (API, mobile SDKs, backend SDKs)
          android-native-sdk/   - Android Native SDK (payment options)
          ios-native-sdk/       - iOS Native SDK (payment options)
          health-check/         - PG Health Check APIs
          tsp/                  - TSP (Third-Party Service Provider) integration
          settlement/           - Settlement APIs
          split-settlement/     - Split Settlement APIs
          chargeback/           - Chargeback management APIs
          native-otp/           - Native OTP APIs
          tpv/                  - Third Party Validation (TPV)
          aggregator/           - API for Aggregators
        """
        sections = doc_service.list_sections()
        body = "\n- ".join(sections)
        return (
            f"Available PhonePe PG documentation sections ({len(sections)} total):\n\n- "
            + body
            + "\n\nUse get_section_content with any of these keys to retrieve full content."
        )

    @mcp.tool()
    def get_section_content(section_key: str) -> str:
        """
        Fetch the full content of a specific PhonePe PG documentation section.

        Use list_doc_sections to get valid section keys.

        Examples:
          'overview'
          'website/standard-checkout/authorization'
          'website/standard-checkout/create-payment'
          'autopay/api/subscription-setup'
          'payment-links/create'
          'custom-checkout-v2/pay/upi-intent'
          'custom-checkout-v2/pay/upi-qr'
          'custom-checkout-v2/mobile/android/introduction'
          'sdk/backend-standard/python/introduction'
          'chargeback/fetch-dispute'
          'health-check/health-check-api'

        Args:
            section_key: Section key from list_doc_sections
        """
        try:
            return doc_service.get_content(section_key)
        except Exception as exc:
            return f"Error: {exc}"

    @mcp.tool()
    def search_docs(keyword: str) -> str:
        """
        Search across all 244+ PhonePe PG documentation sections for a keyword or phrase.

        Returns up to 10 matching sections with relevant snippets. Useful for finding
        docs about a specific feature, error code, or concept without knowing which
        section it belongs to.

        Example keywords:
          'refund', 'UPI', 'webhook', 'oauth', 'mandate', 'card payment',
          'subscription', 'AUTHORIZATION_FAILED', 'TPV', 'settlement', 'chargeback'

        Args:
            keyword: Keyword or phrase to search for in the documentation
        """
        if not keyword or not keyword.strip():
            return "Please provide a non-empty keyword to search for."
        try:
            return doc_service.search(keyword.strip())
        except Exception as exc:
            return f"Search failed: {exc}"

    @mcp.tool()
    def get_api_endpoints() -> str:
        """
        Return all core PhonePe PG API endpoints for Standard Checkout,
        Custom Checkout, and Payment Links — including HTTP method, path, and description.
        """
        return (
            "## PhonePe PG Core API Endpoints\n\n"
            "### Authentication (all environments)\n"
            "| API | Method | Endpoint |\n"
            "|-----|--------|----------|\n"
            "| OAuth Token | POST | /v1/oauth/token |\n\n"
            "### Standard Checkout\n"
            "| API | Method | Endpoint |\n"
            "|-----|--------|----------|\n"
            "| Create Payment | POST | /checkout/v2/pay |\n"
            "| Order Status | GET | /checkout/v2/order/{merchantOrderId}/status |\n\n"
            "### Custom Checkout\n"
            "| API | Method | Endpoint |\n"
            "|-----|--------|----------|\n"
            "| Initiate Payment (UPI QR/Intent/Collect/Card/NB) | POST | /payments/v2/pay |\n"
            "| Order Status | GET | /checkout/v2/order/{merchantOrderId}/status |\n"
            "| Transaction Status | GET | /payments/v2/transaction/{transactionId}/status |\n\n"
            "### Payment Links\n"
            "| API | Method | Endpoint |\n"
            "|-----|--------|----------|\n"
            "| Create Payment Link | POST | /paylinks/v1/pay |\n"
            "| Payment Link Status | GET | /paylinks/v1/{merchantOrderId}/status |\n"
            "| Cancel Payment Link | POST | /paylinks/v1/{merchantOrderId}/cancel |\n"
            "| Resend Notification | POST | /paylinks/v1/notify |\n\n"
            "### Refunds\n"
            "| API | Method | Endpoint |\n"
            "|-----|--------|----------|\n"
            "| Create Refund | POST | /payments/v2/refund |\n"
            "| Refund Status | GET | /payments/v2/refund/{merchantRefundId}/status |\n\n"
            "### Base URLs\n"
            "- **Sandbox:**           https://api-preprod.phonepe.com/apis/pg-sandbox/\n"
            "- **Production (Auth):** https://api.phonepe.com/apis/identity-manager/\n"
            "- **Production (API):**  https://api.phonepe.com/apis/pg/\n\n"
            "For full request/response schemas, use get_section_content with a specific section key.\n"
            "Example: get_section_content('website/standard-checkout/create-payment')"
        )

    @mcp.tool()
    def get_prerequisites(integration_type: str) -> str:
        """
        Return prerequisites and setup requirements for a PhonePe PG integration type.

        Args:
            integration_type: One of: standard-checkout, custom-checkout, autopay,
                              payment-links, mobile-sdk, backend-sdk
        """
        key = integration_type.lower().replace(" ", "-")

        if key in ("standard-checkout", "website"):
            return (
                "## Prerequisites — Standard Checkout\n\n"
                "1. **PhonePe PG Account**: Apply at https://www.phonepe.com/business/\n"
                "2. **API Credentials** (from PhonePe dashboard):\n"
                "   - Client ID, Client Version, Client Secret\n"
                "3. **Environments**:\n"
                "   - Sandbox: https://api-preprod.phonepe.com/apis/pg-sandbox/\n"
                "   - Production Auth: https://api.phonepe.com/apis/identity-manager/\n"
                "   - Production APIs: https://api.phonepe.com/apis/pg/\n"
                "4. A callback/webhook URL for payment status notifications\n"
                "5. The PhonePe JS SDK loaded on your checkout page (required to open the payment page)\n\n"
                "Start with sandbox. Use get_section_content('website/standard-checkout/integration-steps') for step-by-step guidance."
            )
        if key in ("custom-checkout", "custom"):
            return (
                "## Prerequisites — Custom Checkout\n\n"
                "1. All Standard Checkout prerequisites apply.\n"
                "2. **Custom Checkout permission** must be enabled by the PhonePe team — contact your account manager.\n"
                "3. Your app/website renders the payment UI (QR, Intent button, card form, etc.).\n"
                "4. For UPI Collect: validate UPI VPA before initiating payment.\n\n"
                "Use get_section_content('custom-checkout-v2/introduction') for the full guide."
            )
        if key in ("autopay", "recurring", "subscription"):
            return (
                "## Prerequisites — AutoPay / Recurring\n\n"
                "1. All Standard Checkout prerequisites apply.\n"
                "2. **AutoPay permission** must be enabled — contact PhonePe Business Team.\n"
                "3. Understand mandate types: daily, weekly, monthly, yearly, as-presented.\n"
                "4. Handle mandate creation, execution, notify, and cancellation flows.\n\n"
                "Use get_section_content('autopay/api-integration/introduction') for the full guide."
            )
        if key == "payment-links":
            return (
                "## Prerequisites — Payment Links\n\n"
                "### Dashboard (no code required)\n"
                "- Access to PhonePe merchant dashboard — no technical setup needed.\n\n"
                "### API-based\n"
                "1. **Payment Links permission** — contact PhonePe Business Team.\n"
                "2. API credentials (same as standard checkout).\n"
                "3. Webhook URL to receive payment status updates.\n\n"
                "Use get_section_content('payment-links/introduction') for full details."
            )
        if key == "mobile-sdk":
            return (
                "## Prerequisites — Mobile SDK\n\n"
                "1. All Standard Checkout prerequisites apply.\n"
                "2. Platform requirements:\n"
                "   - Android: Android Studio, minSdk 21+\n"
                "   - iOS: Xcode 14+, Swift 5+, CocoaPods or SPM\n"
                "   - Flutter: Flutter SDK 3.x\n"
                "   - React Native: RN 0.70+\n"
                "3. PhonePe app installed on test device for UPI intent flow.\n\n"
                "Use get_section_content('sdk/mobile-standard/android/introduction') for Android setup."
            )
        if key == "backend-sdk":
            return (
                "## Prerequisites — Backend SDK\n\n"
                "1. All Standard Checkout prerequisites apply.\n"
                "2. Language requirements:\n"
                "   - Java: Java 8+, Maven or Gradle\n"
                "   - Python: Python 3.10+, pip\n"
                "   - Node.js: Node.js 16+, npm\n"
                "   - PHP: PHP 7.4+, Composer\n"
                "3. Backend SDK is server-side only — never expose credentials client-side.\n\n"
                "Use get_section_content('sdk/backend-standard/python/introduction') for Python setup."
            )
        return (
            f"Unknown integration type: '{integration_type}'. "
            "Valid types: standard-checkout, custom-checkout, autopay, payment-links, mobile-sdk, backend-sdk"
        )

    @mcp.tool()
    def get_environments() -> str:
        """
        Return PhonePe PG environment base URLs for sandbox (testing) and production.

        Shows which base URL to use for each API in each environment.
        """
        return (
            "## PhonePe PG Environments\n\n"
            "### Sandbox (Testing — no real money)\n"
            "All APIs base URL: https://api-preprod.phonepe.com/apis/pg-sandbox/\n\n"
            "Examples:\n"
            "  POST https://api-preprod.phonepe.com/apis/pg-sandbox/v1/oauth/token\n"
            "  POST https://api-preprod.phonepe.com/apis/pg-sandbox/checkout/v2/pay\n"
            "  GET  https://api-preprod.phonepe.com/apis/pg-sandbox/checkout/v2/order/{id}/status\n\n"
            "### Production\n"
            "OAuth token URL:  https://api.phonepe.com/apis/identity-manager/v1/oauth/token\n"
            "All other APIs:   https://api.phonepe.com/apis/pg/\n\n"
            "Examples:\n"
            "  POST https://api.phonepe.com/apis/identity-manager/v1/oauth/token\n"
            "  POST https://api.phonepe.com/apis/pg/checkout/v2/pay\n"
            "  GET  https://api.phonepe.com/apis/pg/checkout/v2/order/{id}/status\n\n"
            "### Recommendation\n"
            "Always test fully in sandbox before switching to production.\n"
            "Change only the PHONEPE_ENVIRONMENT variable — all API paths are identical in both environments."
        )


def register_kb_tools(mcp: FastMCP) -> None:
    """Register knowledge base tools on the given FastMCP instance."""

    from ..services.kb_service import kb_service

    @mcp.tool()
    def ask_knowledge_base(question: str) -> str:
        """
        Ask a question about PhonePe PG products, features, or APIs.

        This tool answers from a curated knowledge base instantly — no web scraping.
        Best for:
          - Product existence: "Does PhonePe have a Payment Links product?"
          - Feature support: "Does PhonePe support international payments?"
          - Order/payment states: "What are the different states of a payment?"
          - API identification: "What API is used to check chargeback status?"
          - Error explanations: "What does AUTHORIZATION_FAILED mean?"
          - Integration guidance: "What is the difference between Standard and Custom Checkout?"

        If the answer is not in the knowledge base, automatically searches the
        full documentation index as a fallback.

        Args:
            question: Natural language question about PhonePe PG
        """
        if not question or not question.strip():
            return "Please provide a non-empty question."

        # Try knowledge base first
        answer = kb_service.answer_question(question.strip())
        if answer:
            return answer

        # Fall through to doc search
        try:
            search_result = doc_service.search(question.strip())
            if "No results found" not in search_result and "No cached results" not in search_result:
                return (
                    "*(Answer not found directly in knowledge base — showing doc search results)*\n\n"
                    + search_result
                )
        except Exception as exc:
            logger.warning("doc search fallback failed for question '%s': %s", question, exc)

        return (
            f"No direct answer found for: '{question}'.\n\n"
            "Try:\n"
            "  - search_docs with a specific keyword\n"
            "  - list_doc_sections to browse available documentation\n"
            "  - get_section_content with a specific section key"
        )

    @mcp.tool()
    def list_products() -> str:
        """
        List all PhonePe PG products currently live in production.

        Shows product name, permission requirements, and a brief description.
        Covers: Standard Checkout, Custom Checkout, Payment Links, AutoPay,
        Split Settlement, Settlement API, Chargeback API, PG Health Check,
        Native OTP, TPV, TSP Integration, Android/iOS Native SDK, eNACH.
        """
        return kb_service.list_products()

    @mcp.tool()
    def get_feature_support(feature: str) -> str:
        """
        Check whether PhonePe PG supports a specific feature.

        Examples:
          'international_payments'  → No, INR only
          'refunds'                 → Yes, full and partial
          'recurring_payments'      → Yes, UPI AutoPay + eNACH
          'supported_currencies'    → INR only
          'card_networks'           → VISA, MASTERCARD, RUPAY, AMEX
          'mobile_sdk'              → Android, iOS, Flutter, React Native, Ionic
          'backend_sdk'             → Java, Python, NodeJS, PHP
          'emi'                     → Not available
          'webhooks'                → Supported

        Args:
            feature: Feature name (e.g. 'international_payments', 'refunds', 'emi')
        """
        if not feature or not feature.strip():
            return "Please provide a feature name to check."
        return kb_service.get_feature_support(feature.strip())

    @mcp.tool()
    def get_error_code_info(error_code: str) -> str:
        """
        Get the cause and resolution for a PhonePe PG error code.

        Known error codes:
          AUTHORIZATION_FAILED, INVALID_TRANSACTION_ID, BAD_REQUEST,
          FORBIDDEN, INTERNAL_SERVER_ERROR, ORDER_ALREADY_EXISTS,
          REFUND_AMOUNT_EXCEEDS_ORIGINAL, SUBSCRIPTION_NOT_FOUND

        Args:
            error_code: PhonePe error code (e.g. 'AUTHORIZATION_FAILED')
        """
        if not error_code or not error_code.strip():
            return "Please provide an error code."
        return kb_service.get_error_code_info(error_code.strip())
