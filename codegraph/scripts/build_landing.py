#!/usr/bin/env python3
"""
Landing Page Build Script

Builds index.html and whitepaper.html from templates with shared header/footer components
and modular sections.
"""

import re
from pathlib import Path
from datetime import date
from typing import Dict, List, Optional

# Paths
LANDING_DIR = Path(__file__).parent.parent / "docs" / "landing"
TEMPLATES_DIR = LANDING_DIR / "templates"
SECTIONS_DIR = TEMPLATES_DIR / "sections"
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

# Section order for index.html
INDEX_SECTIONS = [
    "hero",
    "problems",
    "solution",
    "features",
    "metrics",
    "integrations",
    "architecture",
    "usp",
    "faq",
    "cta",
]


def load_template(name: str) -> str:
    """Load a template file."""
    template_path = TEMPLATES_DIR / name
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")
    return template_path.read_text(encoding="utf-8")


def load_section(name: str) -> str:
    """Load a section template file."""
    section_path = SECTIONS_DIR / f"{name}.html"
    if not section_path.exists():
        raise FileNotFoundError(f"Section not found: {section_path}")
    return section_path.read_text(encoding="utf-8")


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


def render_sections(section_names: List[str]) -> str:
    """Render multiple sections and join them."""
    sections = []
    for name in section_names:
        try:
            section_content = load_section(name)
            sections.append(section_content.strip())
        except FileNotFoundError as e:
            print(f"Warning: {e}")
            continue
    return "\n\n    ".join(sections)


def update_html_file(filepath: Path, header_html: str, footer_html: str) -> None:
    """Update an HTML file with new header and footer."""
    content = filepath.read_text(encoding="utf-8")

    # Replace header (from <!-- Header --> to </header>, including any template comments)
    header_pattern = r'<!-- Header -->.*?</header>\s*(?=<!-- Mobile Navigation -->|</nav>)'
    # Match the full header block including mobile nav
    header_full_pattern = r'<!-- Header -->.*?</header>\s*<!-- Mobile Navigation -->.*?</nav>\s*</header>'

    # Try full pattern first (includes mobile nav inside header)
    if re.search(header_full_pattern, content, flags=re.DOTALL):
        content = re.sub(header_full_pattern, header_html.strip(), content, flags=re.DOTALL)
    else:
        # Fallback: match header with any content between marker and closing tag
        simple_pattern = r'<!-- Header -->.*?</header>'
        content = re.sub(simple_pattern, header_html.strip(), content, flags=re.DOTALL)

    # Replace footer (from <!-- Footer --> to </footer>)
    footer_pattern = r'<!-- Footer -->.*?</footer>'
    content = re.sub(footer_pattern, footer_html.strip(), content, flags=re.DOTALL)

    filepath.write_text(content, encoding="utf-8")
    print(f"Updated: {filepath}")


def build_index_from_sections():
    """Build index.html from modular sections."""
    print("Building index.html from sections...")

    # Load head template
    head_html = """<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="description" content="CodeGraph - AI-копилот для анализа исходного кода на основе Code Property Graph. Enterprise-ready решение для статического анализа, security audit и code review.">
  <meta name="keywords" content="CodeGraph, CPG, Code Property Graph, статический анализ, SAST, code review, AI копилот, security audit, enterprise">
  <meta property="og:title" content="CodeGraph - AI-копилот для анализа кода">
  <meta property="og:description" content="Enterprise-ready AI-копилот для глубокого анализа исходного кода на основе Code Property Graph">
  <meta property="og:type" content="website">
  <meta property="og:url" content="https://codegraph.ru">
  <meta property="og:image" content="https://codegraph.ru/assets/og-image.png">
  <title>CodeGraph - AI-копилот для анализа исходного кода | CPG + Hybrid RAG</title>
  <link rel="icon" href="assets/favicon.svg" type="image/svg+xml">
  <link rel="stylesheet" href="css/styles.css">
  <!-- Preconnect for fonts -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
</head>
<body>
"""

    # Render components
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

    # Render all sections
    sections_html = render_sections(INDEX_SECTIONS)

    # Scripts section
    scripts_html = """
  <!-- Scripts -->
  <script src="js/main.js"></script>
</body>
</html>
"""

    # Assemble full page
    full_html = (
        head_html +
        "  <!-- Header -->\n  " + header.strip() + "\n\n" +
        "  <main>\n    " + sections_html + "\n  </main>\n\n" +
        "  <!-- Footer -->\n  " + footer.strip() + "\n\n" +
        scripts_html
    )

    # Write output
    output_path = OUTPUT_DIR / "index.html"
    output_path.write_text(full_html, encoding="utf-8")
    print(f"Built: {output_path}")


def build_index():
    """Build index.html with shared components (legacy mode for header/footer only)."""
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
    import sys

    print("Building landing pages...")
    print(f"Templates dir: {TEMPLATES_DIR}")
    print(f"Sections dir: {SECTIONS_DIR}")
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

    # Check command line args
    if len(sys.argv) > 1 and sys.argv[1] == "--sections":
        # Build from sections (new modular approach)
        if not SECTIONS_DIR.exists():
            print(f"Error: Sections directory not found: {SECTIONS_DIR}")
            return 1
        build_index_from_sections()
    else:
        # Legacy mode: update header/footer only
        build_index()

    # Always update whitepaper
    build_whitepaper()

    print("Done!")
    return 0


if __name__ == "__main__":
    exit(main())
