"""
HTML Template Engine

Generates styled HTML documentation pages based on whitepaper.html template.
"""

from datetime import date
from typing import List, Dict, Optional
from pathlib import Path

from .config import CSS_PATH, JS_PATH, ASSETS_PATH, UI_STRINGS, DOC_SECTIONS


# Main HTML template based on whitepaper.html structure
HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="{lang}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="description" content="{description}">
  <meta name="keywords" content="CodeGraph, documentation, {keywords}">

  <meta property="og:title" content="{title} - CodeGraph">
  <meta property="og:description" content="{description}">
  <meta property="og:type" content="article">

  <title>{title} - CodeGraph Documentation</title>

  <link rel="icon" type="image/svg+xml" href="{assets_path}/svg/logo-compact.svg">
  <link rel="stylesheet" href="{css_path}">
</head>
<body>
  <!-- Header -->
  <header class="header">
    <nav class="nav container">
      <a href="{home_url}" class="logo">
        <img src="{assets_path}/svg/logo.svg" alt="CodeGraph" width="160" height="40">
      </a>

      <ul class="nav-list">
        <li><a href="{home_url}index.html#problems" class="nav-link">{ui_problems}</a></li>
        <li><a href="{home_url}index.html#solution" class="nav-link">{ui_solution}</a></li>
        <li><a href="{home_url}index.html#features" class="nav-link">{ui_features}</a></li>
        <li><a href="{home_url}index.html#integrations" class="nav-link">{ui_integrations}</a></li>
        <li><a href="{docs_index_url}" class="nav-link active">{ui_docs}</a></li>
        <li><a href="{home_url}index.html#faq" class="nav-link">{ui_faq}</a></li>
      </ul>

      <div class="header-actions">
        <div class="lang-switcher">
          <a href="{en_url}" class="{en_class}">EN</a>
          <a href="{ru_url}" class="{ru_class}">RU</a>
        </div>
        <button class="theme-toggle" aria-label="{ui_toggle_theme}">
          <svg class="icon-sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20">
            <circle cx="12" cy="12" r="5"/>
            <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
          </svg>
          <svg class="icon-moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20">
            <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
          </svg>
        </button>
        <a href="{home_url}index.html#demo" class="btn btn-primary">{ui_request_demo}</a>
      </div>

      <button class="mobile-menu-toggle" aria-label="Menu">
        <span></span>
        <span></span>
        <span></span>
      </button>
    </nav>
    <!-- Mobile Navigation -->
    <nav class="mobile-nav">
      <ul class="mobile-nav-list">
        <li><a href="{home_url}index.html#problems" class="mobile-nav-link">{ui_problems}</a></li>
        <li><a href="{home_url}index.html#solution" class="mobile-nav-link">{ui_solution}</a></li>
        <li><a href="{home_url}index.html#features" class="mobile-nav-link">{ui_features}</a></li>
        <li><a href="{home_url}index.html#integrations" class="mobile-nav-link">{ui_integrations}</a></li>
        <li><a href="{docs_index_url}" class="mobile-nav-link">{ui_docs}</a></li>
        <li><a href="{home_url}index.html#faq" class="mobile-nav-link">{ui_faq}</a></li>
        <li><a href="{home_url}index.html#demo" class="btn btn-primary mobile-nav-demo-btn">{ui_request_demo}</a></li>
      </ul>
    </nav>
  </header>

  <div class="doc-layout">
    <!-- Sidebar Navigation -->
    <aside class="doc-sidebar">
      {sidebar_html}
    </aside>

    <!-- Main Content -->
    <main class="doc-main">
      <!-- Breadcrumb -->
      <nav class="doc-breadcrumb">
        <a href="{docs_index_url}">{ui_docs}</a>
        <span>/</span>
        <a href="{section_url}">{section_title}</a>
        <span>/</span>
        <span>{title}</span>
      </nav>

      <!-- Hero -->
      <div class="doc-hero">
        <h1>{title}</h1>
        {subtitle_html}
      </div>

      <!-- Content -->
      <article class="doc-content">
        {content}
      </article>

      <!-- Page Navigation -->
      {prev_next_nav}

      <!-- Footer -->
      <footer class="doc-footer">
        <span>{ui_last_updated}: {update_date}</span>
        <a href="{edit_url}" target="_blank" rel="noopener">{ui_edit_text}</a>
      </footer>
    </main>

    <!-- Table of Contents -->
    <aside class="doc-toc">
      <div class="doc-toc-title">{ui_on_this_page}</div>
      <ul class="doc-toc-list">
        {toc_html}
      </ul>
    </aside>
  </div>

  <!-- Footer -->
  <footer class="footer">
    <div class="container">
      <div class="footer-content">
        <div class="footer-brand">
          <img src="{assets_path}/svg/logo.svg" alt="CodeGraph" width="160" height="40">
          <p>{ui_footer_tagline}</p>
        </div>
        <div class="footer-links">
          <div class="footer-links-group">
            <h4>{ui_footer_product}</h4>
            <ul class="footer-links-list">
              <li><a href="{home_url}index.html#features" class="footer-link">{ui_features}</a></li>
              <li><a href="{home_url}index.html#integrations" class="footer-link">{ui_integrations}</a></li>
              <li><a href="{home_url}index.html#faq" class="footer-link">{ui_faq}</a></li>
            </ul>
          </div>
          <div class="footer-links-group">
            <h4>{ui_footer_docs}</h4>
            <ul class="footer-links-list">
              <li><a href="{docs_base_url}/getting-started/index.html" class="footer-link">{ui_footer_getting_started}</a></li>
              <li><a href="{docs_base_url}/guides/index.html" class="footer-link">{ui_footer_guides}</a></li>
              <li><a href="{docs_base_url}/api/index.html" class="footer-link">{ui_footer_api}</a></li>
              <li><a href="{docs_base_url}/enterprise/index.html" class="footer-link">{ui_footer_enterprise}</a></li>
            </ul>
          </div>
          <div class="footer-links-group">
            <h4>{ui_footer_resources}</h4>
            <ul class="footer-links-list">
              <li><a href="{whitepaper_url}" class="footer-link">{ui_footer_whitepaper}</a></li>
            </ul>
          </div>
          <div class="footer-links-group">
            <h4>{ui_footer_contacts}</h4>
            <ul class="footer-links-list">
              <li><a href="mailto:hello@codegraph.ru" class="footer-link">hello@codegraph.ru</a></li>
              <li><a href="https://t.me/codegraph" class="footer-link" target="_blank" rel="noopener">Telegram</a></li>
              <li><a href="https://github.com/codegraph" class="footer-link" target="_blank" rel="noopener">GitHub</a></li>
            </ul>
            <div class="footer-social">
              <a href="https://t.me/codegraph" class="footer-social-link" target="_blank" rel="noopener" aria-label="Telegram">
                <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
                  <path d="M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z"/>
                </svg>
              </a>
              <a href="https://github.com/codegraph" class="footer-social-link" target="_blank" rel="noopener" aria-label="GitHub">
                <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
                  <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
                </svg>
              </a>
            </div>
          </div>
        </div>
      </div>
      <div class="footer-bottom">
        <p>&copy; {year} CodeGraph. {ui_rights_reserved}</p>
      </div>
    </div>
  </footer>

  <script src="{js_path}"></script>
</body>
</html>
'''


class HTMLGenerator:
    """Generates HTML documentation pages from templates."""

    def __init__(self, lang: str = 'en'):
        """
        Initialize generator for specific language.

        Args:
            lang: Language code ('en' or 'ru')
        """
        self.lang = lang
        self.ui = UI_STRINGS.get(lang, UI_STRINGS['en'])

    def generate(
        self,
        title: str,
        content: str,
        relative_path: str,
        section_id: str,
        headings: List[Dict] = None,
        sidebar_html: str = "",
        subtitle: str = "",
        description: str = "",
        prev_page: Dict = None,
        next_page: Dict = None,
    ) -> str:
        """
        Generate complete HTML page.

        Args:
            title: Page title
            content: HTML content (already converted from Markdown)
            relative_path: Path relative to docs root (e.g., 'guides/CLI_GUIDE')
            section_id: Section identifier (e.g., 'guides')
            headings: List of headings for TOC
            sidebar_html: Pre-rendered sidebar HTML
            subtitle: Optional subtitle
            description: Meta description

        Returns:
            Complete HTML page string
        """
        headings = headings or []
        other_lang = 'ru' if self.lang == 'en' else 'en'

        # Get section metadata
        section = self._get_section(section_id)
        section_title = section.get(f'title_{self.lang}', section_id.title())

        # Calculate URLs
        # From docs/landing/docs/en/guides/file.html back to docs/landing/
        depth = relative_path.count('/') + 2  # +2 for docs/en or docs/ru
        base_prefix = '../' * depth

        # Calculate docs base URL for footer links
        docs_base_url = ".."  # From section/file.html to docs/lang/ (no trailing slash)
        whitepaper_url = f"{base_prefix}whitepaper.html"  # Direct link to whitepaper

        # Calculate language switcher URLs
        # From section/file.html need to go up to lang root, then to other lang
        lang_switch_prefix = '../' * (relative_path.count('/') + 1)  # +1 to exit section folder and lang folder

        return HTML_TEMPLATE.format(
            lang=self.lang,
            title=title,
            description=description or f"CodeGraph documentation: {title}",
            keywords=section_id,
            subtitle_html=f'<p class="subtitle">{subtitle}</p>' if subtitle else '',
            content=content,
            sidebar_html=sidebar_html,
            toc_html=self._generate_toc(headings),
            prev_next_nav=self._generate_prev_next_nav(prev_page, next_page),

            # URLs
            css_path=CSS_PATH,
            js_path=JS_PATH,
            assets_path=ASSETS_PATH,
            home_url=f"{base_prefix}",
            whitepaper_url=whitepaper_url,
            docs_index_url=f"../index.html",
            docs_base_url=docs_base_url,
            section_url=f"index.html",
            en_url=f"{lang_switch_prefix}en/{relative_path}.html",
            ru_url=f"{lang_switch_prefix}ru/{relative_path}.html",
            edit_url=f"https://github.com/your-org/codegraph/edit/main/docs/{relative_path}.md",

            # Language switcher classes
            en_class="active" if self.lang == 'en' else "",
            ru_class="active" if self.lang == 'ru' else "",

            # Section info
            section_title=section_title,

            # Dates
            update_date=date.today().strftime("%Y-%m-%d"),
            year=date.today().year,

            # UI strings - Navigation
            ui_problems=self.ui['nav_problems'],
            ui_solution=self.ui['nav_solution'],
            ui_features=self.ui['nav_features'],
            ui_integrations=self.ui['nav_integrations'],
            ui_docs=self.ui['nav_docs'],
            ui_faq=self.ui['nav_faq'],
            ui_request_demo=self.ui['nav_request_demo'],
            ui_toggle_theme=self.ui['toggle_theme'],
            # UI strings - Documentation
            ui_last_updated=self.ui['last_updated'],
            ui_edit_text=self.ui['edit_text'],
            ui_on_this_page=self.ui['on_this_page'],
            # UI strings - Footer
            ui_footer_tagline=self.ui['footer_tagline'],
            ui_footer_product=self.ui['footer_product'],
            ui_footer_docs=self.ui['footer_docs'],
            ui_footer_resources=self.ui['footer_resources'],
            ui_footer_contacts=self.ui['footer_contacts'],
            ui_footer_getting_started=self.ui['footer_getting_started'],
            ui_footer_guides=self.ui['footer_guides'],
            ui_footer_api=self.ui['footer_api'],
            ui_footer_enterprise=self.ui['footer_enterprise'],
            ui_footer_whitepaper=self.ui['footer_whitepaper'],
            ui_rights_reserved=self.ui['rights_reserved'],
        )

    def _get_section(self, section_id: str) -> dict:
        """Get section metadata by ID."""
        for section in DOC_SECTIONS:
            if section['id'] == section_id:
                return section
        return {'id': section_id, 'title_en': section_id.title(), 'title_ru': section_id.title()}

    def _generate_toc(self, headings: List[Dict]) -> str:
        """Generate table of contents HTML from headings."""
        if not headings:
            return ""

        items = []
        for heading in headings:
            level = heading.get('level', 2)
            text = heading.get('text', '')
            slug = heading.get('slug', '')

            if level > 3:  # Only show H2 and H3
                continue

            level_class = f"level-{level}"
            items.append(f'<li><a href="#{slug}" class="{level_class}">{text}</a></li>')

        return '\n'.join(items)

    def _generate_prev_next_nav(self, prev_page: Dict, next_page: Dict) -> str:
        """
        Generate prev/next navigation HTML.

        Args:
            prev_page: Dict with 'url' and 'title' keys for previous page
            next_page: Dict with 'url' and 'title' keys for next page

        Returns:
            HTML string for navigation, or empty string if no navigation
        """
        if not prev_page and not next_page:
            return ""

        nav_parts = ['<nav class="doc-page-nav">']

        if prev_page:
            nav_parts.append(f'''
      <a href="{prev_page['url']}" class="doc-page-nav-prev">
        <span class="doc-page-nav-label">{self.ui['nav_prev']}</span>
        <span class="doc-page-nav-title">{prev_page['title']}</span>
      </a>''')
        else:
            nav_parts.append('      <span></span>')  # Placeholder for flex alignment

        if next_page:
            nav_parts.append(f'''
      <a href="{next_page['url']}" class="doc-page-nav-next">
        <span class="doc-page-nav-label">{self.ui['nav_next']}</span>
        <span class="doc-page-nav-title">{next_page['title']}</span>
      </a>''')

        nav_parts.append('    </nav>')
        return '\n'.join(nav_parts)


def generate_sidebar(sections: List[Dict], current_path: str, lang: str) -> str:
    """
    Generate sidebar navigation HTML.

    Args:
        sections: List of section configurations
        current_path: Current page path for highlighting
        lang: Language code

    Returns:
        HTML string for sidebar
    """
    html_parts = []

    for section in sections:
        section_id = section['id']
        title_key = f"title_{lang}"
        title = section.get(title_key, section_id.title())

        html_parts.append(f'''
        <div class="doc-sidebar-section">
          <div class="doc-sidebar-title">{title}</div>
          <ul class="doc-sidebar-nav">
            <li><a href="{section_id}/index.html">Overview</a></li>
          </ul>
        </div>
        ''')

    return '\n'.join(html_parts)
