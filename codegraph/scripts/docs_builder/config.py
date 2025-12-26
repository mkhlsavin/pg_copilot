"""
Configuration for Documentation Builder

Contains all constants and settings for the documentation build process.
"""

from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
DOCS_ROOT = PROJECT_ROOT / "docs"

# Source folders to process
SOURCE_FOLDERS = [
    "getting-started",
    "guides",
    "api",
    "integrations",
    "reference",
    "enterprise",
]

# Output directories
OUTPUT_BASE = Path("docs/landing/docs")
OUTPUT_EN = OUTPUT_BASE / "en"
OUTPUT_RU = OUTPUT_BASE / "ru"

# Folders with bilingual structure (have en/ and ru/ subfolders)
# All documentation sections now use this structure
BILINGUAL_FOLDERS = [
    "getting-started",
    "guides",
    "api",
    "integrations",
    "reference",
    "enterprise",
    "sber500",
]

# Translation settings
TRANSLATION_CACHE_DIR = PROJECT_ROOT / ".doc_translation_cache"
TRANSLATION_BATCH_SIZE = 3
MAX_CONTENT_LENGTH = 8000  # Characters before splitting

# Template paths (relative from output HTML at section/file.html level)
# Files are at: docs/landing/docs/en/section/file.html
# CSS is at: docs/landing/css/styles.css
# So we need 3 levels up: ../../../css/styles.css
# Version query param for cache busting after CSS modularization
CSS_PATH = "../../../css/styles.css?v=2"
JS_PATH = "../../../js/main.js"
ASSETS_PATH = "../../../assets"

# Documentation sections with metadata
DOC_SECTIONS = [
    {
        "id": "getting-started",
        "title_en": "Getting Started",
        "title_ru": "Начало работы",
        "order": 1,
        "icon": "icon-onboarding.svg",
    },
    {
        "id": "guides",
        "title_en": "User Guides",
        "title_ru": "Руководства",
        "order": 2,
        "icon": "icon-docs.svg",
    },
    {
        "id": "api",
        "title_en": "API Reference",
        "title_ru": "API Документация",
        "order": 3,
        "icon": "icon-integration.svg",
    },
    {
        "id": "integrations",
        "title_en": "Integrations",
        "title_ru": "Интеграции",
        "order": 4,
        "icon": "icon-integration.svg",
    },
    {
        "id": "reference",
        "title_en": "Technical Reference",
        "title_ru": "Справочник",
        "order": 5,
        "icon": "icon-architecture.svg",
    },
    {
        "id": "enterprise",
        "title_en": "Enterprise",
        "title_ru": "Enterprise",
        "order": 6,
        "icon": "icon-security.svg",
    },
]

# UI translations
UI_STRINGS = {
    "en": {
        # Navigation
        "nav_problems": "Problems",
        "nav_solution": "Solution",
        "nav_features": "Features",
        "nav_integrations": "Integrations",
        "nav_docs": "Documentation",
        "nav_faq": "FAQ",
        "nav_demo": "Demo",
        "nav_request_demo": "Request Demo",
        "toggle_theme": "Toggle theme",
        # Documentation
        "back_text": "Back to docs",
        "last_updated": "Last updated",
        "edit_text": "Edit on GitHub",
        "search_placeholder": "Search documentation...",
        "toc_title": "Table of Contents",
        "on_this_page": "On this page",
        # Footer
        "footer_tagline": "AI copilot for source code analysis",
        "footer_product": "Product",
        "footer_docs": "Documentation",
        "footer_resources": "Resources",
        "footer_contacts": "Contacts",
        "footer_getting_started": "Getting Started",
        "footer_guides": "Guides",
        "footer_api": "API",
        "footer_enterprise": "Enterprise",
        "footer_whitepaper": "Whitepaper",
        "footer_docs_en": "Docs (EN)",
        "rights_reserved": "All rights reserved.",
        # Navigation
        "nav_prev": "Previous",
        "nav_next": "Next",
    },
    "ru": {
        # Navigation
        "nav_problems": "Проблемы",
        "nav_solution": "Решение",
        "nav_features": "Возможности",
        "nav_integrations": "Интеграции",
        "nav_docs": "Документация",
        "nav_faq": "FAQ",
        "nav_demo": "Демо",
        "nav_request_demo": "Запросить демо",
        "toggle_theme": "Переключить тему",
        # Documentation
        "back_text": "К документации",
        "last_updated": "Обновлено",
        "edit_text": "Редактировать на GitHub",
        "search_placeholder": "Поиск по документации...",
        "toc_title": "Содержание",
        "on_this_page": "На этой странице",
        # Footer
        "footer_tagline": "AI-копилот для анализа исходного кода",
        "footer_product": "Продукт",
        "footer_docs": "Документация",
        "footer_resources": "Ресурсы",
        "footer_contacts": "Контакты",
        "footer_getting_started": "Начало работы",
        "footer_guides": "Руководства",
        "footer_api": "API",
        "footer_enterprise": "Enterprise",
        "footer_whitepaper": "Whitepaper",
        "footer_docs_en": "Docs (EN)",
        "rights_reserved": "Все права защищены.",
        # Navigation
        "nav_prev": "Назад",
        "nav_next": "Вперед",
    },
}

# Order of files in each section for navigation
# Files not listed will be appended alphabetically
FILE_ORDER = {
    "getting-started": [
        "INSTALLATION",
        "CONFIGURATION",
    ],
    "guides": [
        "QUICK_REFERENCE",
        "TUI_USER_GUIDE",
        "CLI_GUIDE",
        "PROGRAMMATIC_GUIDE",
        "PROJECT_IMPORT",
        "CPG_EXPORT",
        "CODE_REVIEW",
        "REFACTORING",
        "BENCHMARK_GUIDE",
        "MONITORING",
        "TROUBLESHOOTING",
        "SCENARIOS",
        # Сценарии (01-16) добавятся автоматически по номеру
    ],
    "api": [
        "REST_API",
        "WEBSOCKET_API",
    ],
    "integrations": [
        "GIGACHAT",
        "YANDEX_AI_STUDIO",
    ],
    "reference": [
        "SCHEMA",
        "SQL_QUERY_COOKBOOK",
        "AGENTS",
        "WORKFLOWS",
        "HYPOTHESIS_SYSTEM",
        "API",
        "ANALYSIS_MODULES",
        "SECURITY",
    ],
    "enterprise": [
        "DEPLOYMENT_GUIDE",
        "SECURITY_BRIEF",
        "RBAC",
        "DLP_SECURITY",
        "LLM_SECURITY",
        "SIEM",
        "HYPOTHESIS_WHITEPAPER",
        "COMPETITIVE_MATRIX",
    ],
}
