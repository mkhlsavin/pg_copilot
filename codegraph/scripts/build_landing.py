#!/usr/bin/env python3
"""
Landing Page Build Script

Builds index.html and whitepaper.html from templates with shared header/footer components.
"""

import re
from pathlib import Path
from datetime import date
from typing import Dict

# Paths
LANDING_DIR = Path(__file__).parent.parent / "docs" / "landing"
TEMPLATES_DIR = LANDING_DIR / "templates"
OUTPUT_DIR = LANDING_DIR


# UI Strings for different languages
UI_STRINGS = {
    "ru": {
        "nav_problems": "Проблемы",
        "nav_solution": "Решение",
        "nav_features": "Возможности",
        "nav_integrations": "Интеграции",
        "nav_docs": "Документация",
        "nav_faq": "FAQ",
        "nav_request_demo": "Запросить демо",
        "toggle_theme": "Переключить тему",
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
        "rights_reserved": "Все права защищены.",
    }
}


def load_template(name: str) -> str:
    """Load a template file."""
    template_path = TEMPLATES_DIR / name
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")
    return template_path.read_text(encoding="utf-8")


def render_header(
    base_url: str = "",
    docs_url: str = "docs/ru/index.html",
    lang_switcher: str = "",
    lang: str = "ru"
) -> str:
    """Render header component with given parameters."""
    template = load_template("header.html")
    ui = UI_STRINGS.get(lang, UI_STRINGS["ru"])

    return template.format(
        base_url=base_url,
        docs_url=docs_url,
        lang_switcher=lang_switcher,
        nav_problems=ui["nav_problems"],
        nav_solution=ui["nav_solution"],
        nav_features=ui["nav_features"],
        nav_integrations=ui["nav_integrations"],
        nav_docs=ui["nav_docs"],
        nav_faq=ui["nav_faq"],
        nav_request_demo=ui["nav_request_demo"],
        toggle_theme=ui["toggle_theme"],
    )


def render_footer(
    base_url: str = "",
    docs_url_base: str = "docs/ru",
    lang: str = "ru"
) -> str:
    """Render footer component with given parameters."""
    template = load_template("footer.html")
    ui = UI_STRINGS.get(lang, UI_STRINGS["ru"])

    return template.format(
        base_url=base_url,
        docs_url_base=docs_url_base,
        footer_tagline=ui["footer_tagline"],
        footer_product=ui["footer_product"],
        footer_docs=ui["footer_docs"],
        footer_resources=ui["footer_resources"],
        footer_contacts=ui["footer_contacts"],
        nav_features=ui["nav_features"],
        nav_integrations=ui["nav_integrations"],
        nav_faq=ui["nav_faq"],
        footer_getting_started=ui["footer_getting_started"],
        footer_guides=ui["footer_guides"],
        footer_api=ui["footer_api"],
        footer_enterprise=ui["footer_enterprise"],
        footer_whitepaper=ui["footer_whitepaper"],
        year=f"2024-{date.today().year}",
        rights_reserved=ui["rights_reserved"],
    )


def update_html_file(filepath: Path, header_html: str, footer_html: str) -> None:
    """Update an HTML file with new header and footer."""
    content = filepath.read_text(encoding="utf-8")

    # Replace header (from <!-- Header --> to </header>)
    header_pattern = r'<!-- Header -->\s*<header class="header">.*?</header>'
    content = re.sub(header_pattern, header_html.strip(), content, flags=re.DOTALL)

    # Replace footer (from <!-- Footer --> to </footer> for main footer)
    # Be careful to only match the main page footer, not the doc-footer
    footer_pattern = r'<!-- Footer -->\s*<footer class="footer">.*?</footer>\s*(?=\s*<!--|\s*<script)'
    content = re.sub(footer_pattern, footer_html.strip() + "\n\n  ", content, flags=re.DOTALL)

    filepath.write_text(content, encoding="utf-8")
    print(f"Updated: {filepath}")


def build_index():
    """Build index.html with shared components."""
    header = render_header(
        base_url="",
        docs_url="docs/ru/index.html",
        lang_switcher="",  # No language switcher on landing pages
        lang="ru"
    )

    footer = render_footer(
        base_url="",
        docs_url_base="docs/ru",
        lang="ru"
    )

    # Add the comment markers
    header_with_marker = "<!-- Header -->\n" + header
    footer_with_marker = "<!-- Footer -->\n" + footer

    update_html_file(OUTPUT_DIR / "index.html", header_with_marker, footer_with_marker)


def build_whitepaper():
    """Build whitepaper.html with shared components."""
    header = render_header(
        base_url="",
        docs_url="docs/ru/index.html",
        lang_switcher="",
        lang="ru"
    )

    footer = render_footer(
        base_url="",
        docs_url_base="docs/ru",
        lang="ru"
    )

    header_with_marker = "<!-- Header -->\n" + header
    footer_with_marker = "<!-- Footer -->\n" + footer

    update_html_file(OUTPUT_DIR / "whitepaper.html", header_with_marker, footer_with_marker)


def main():
    """Main build function."""
    print("Building landing pages...")
    print(f"Templates dir: {TEMPLATES_DIR}")
    print(f"Output dir: {OUTPUT_DIR}")

    # Check templates exist
    if not TEMPLATES_DIR.exists():
        print(f"Error: Templates directory not found: {TEMPLATES_DIR}")
        return 1

    for template_name in ["header.html", "footer.html"]:
        template_path = TEMPLATES_DIR / template_name
        if not template_path.exists():
            print(f"Error: Template not found: {template_path}")
            return 1

    # Build pages
    build_index()
    build_whitepaper()

    print("Done!")
    return 0


if __name__ == "__main__":
    exit(main())
