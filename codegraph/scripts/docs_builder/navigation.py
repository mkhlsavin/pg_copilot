"""
Navigation Generator

Generates sidebar navigation, index pages, and breadcrumbs.
"""

from datetime import date
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass

from .config import DOC_SECTIONS, UI_STRINGS, CSS_PATH, JS_PATH, ASSETS_PATH, FILE_ORDER


@dataclass
class NavItem:
    """Navigation item."""
    title: str
    url: str
    is_active: bool = False
    children: List['NavItem'] = None

    def __post_init__(self):
        if self.children is None:
            self.children = []


def sort_files_by_order(files: List[Dict], section_id: str) -> List[Dict]:
    """
    Sort files according to FILE_ORDER config.

    Files listed in FILE_ORDER come first in that order.
    Scenario files (01-16) are sorted by number.
    Remaining files are sorted alphabetically.

    Args:
        files: List of file info dicts with 'slug' key
        section_id: Section identifier

    Returns:
        Sorted list of file info dicts
    """
    order = FILE_ORDER.get(section_id, [])

    def sort_key(f):
        slug = f['slug']
        # Skip index/readme - they shouldn't be in the list
        if slug.lower() in ('index', 'readme'):
            return (3, slug)
        # Files in explicit order come first
        if slug in order:
            return (0, order.index(slug))
        # Scenario files (01-onboarding, 02-security, etc.) sorted by number
        if len(slug) > 2 and slug[:2].isdigit() and '-' in slug:
            return (1, slug)
        # Everything else alphabetically at the end
        return (2, slug)

    return sorted(files, key=sort_key)


def generate_sidebar_html(
    sections: List[Dict],
    files_by_section: Dict[str, List[Dict]],
    current_path: str,
    lang: str
) -> str:
    """
    Generate sidebar navigation HTML.

    Args:
        sections: Section configurations from DOC_SECTIONS
        files_by_section: Dict mapping section_id to list of file info dicts
        current_path: Current page path for highlighting (e.g., 'api/REST_API.html')
        lang: Language code

    Returns:
        HTML string for sidebar
    """
    html_parts = []

    # Calculate current section from path
    current_section = current_path.split('/')[0] if '/' in current_path else ''

    for section in sections:
        section_id = section['id']
        title_key = f"title_{lang}"
        title = section.get(title_key, section_id.title())

        # Get files for this section
        files = files_by_section.get(section_id, [])

        html_parts.append(f'''
    <div class="doc-sidebar-section">
      <div class="doc-sidebar-title">{title}</div>
      <ul class="doc-sidebar-nav">''')

        # Calculate relative path prefix
        # If we're in a different section, we need to go up one level first
        if current_section and current_section != section_id:
            prefix = f"../{section_id}/"
        else:
            prefix = "" if current_section == section_id else f"{section_id}/"

        # Add section index link
        index_url = f"{prefix}index.html"
        is_active = current_path == f"{section_id}/index.html"
        active_class = ' class="active"' if is_active else ''
        overview = "Overview" if lang == 'en' else "Обзор"
        html_parts.append(f'        <li><a href="{index_url}"{active_class}>{overview}</a></li>')

        # Add file links
        for file_info in files:
            file_url = f"{prefix}{file_info['slug']}.html"
            is_active = current_path == f"{section_id}/{file_info['slug']}.html"
            active_class = ' class="active"' if is_active else ''

            # Use Russian title if available for RU language
            if lang == 'ru' and 'title_ru' in file_info:
                file_title = file_info['title_ru']
            else:
                file_title = file_info.get('title', file_info['slug'])

            # Skip README/index files (already shown as Overview)
            if file_info['slug'].lower() in ('readme', 'index'):
                continue

            html_parts.append(f'        <li><a href="{file_url}"{active_class}>{file_title}</a></li>')

        html_parts.append('''      </ul>
    </div>''')

    return '\n'.join(html_parts)


def generate_index_page(
    lang: str,
    sections: List[Dict],
    files_by_section: Dict[str, List[Dict]]
) -> str:
    """
    Generate main documentation index page.

    Args:
        lang: Language code
        sections: Section configurations
        files_by_section: Files organized by section

    Returns:
        Complete HTML for index page
    """
    ui = UI_STRINGS.get(lang, UI_STRINGS['en'])
    other_lang = 'ru' if lang == 'en' else 'en'

    # Language switcher classes
    en_class = "active" if lang == 'en' else ""
    ru_class = "active" if lang == 'ru' else ""

    # Title and description
    if lang == 'ru':
        title = "Документация CodeGraph"
        description = "Полное руководство по использованию CodeGraph"
        welcome = "Добро пожаловать в документацию CodeGraph"
        welcome_desc = "Выберите раздел для начала работы"
    else:
        title = "CodeGraph Documentation"
        description = "Complete guide to using CodeGraph"
        welcome = "Welcome to CodeGraph Documentation"
        welcome_desc = "Choose a section to get started"

    # Generate section cards
    cards_html = []
    for section in sections:
        section_id = section['id']
        title_key = f"title_{lang}"
        section_title = section.get(title_key, section_id.title())
        icon = section.get('icon', 'icon-docs.svg')

        # Count files in section (excluding README and index)
        all_files = files_by_section.get(section_id, [])
        file_count = len([f for f in all_files if f['slug'].lower() not in ('readme', 'index')])

        # Get first few file titles for preview
        files = files_by_section.get(section_id, [])[:3]

        def get_file_title(f, lang):
            """Get file title in appropriate language."""
            if lang == 'ru' and 'title_ru' in f:
                return f['title_ru']
            return f.get('title', f['slug'])

        preview_items = ''.join(
            f'<li>{get_file_title(f, lang)}</li>'
            for f in files if f['slug'].lower() not in ('readme', 'index')
        )

        cards_html.append(f'''
      <a href="{section_id}/index.html" class="doc-card">
        <div class="doc-card-icon">
          <img src="../../assets/svg/{icon}" alt="" width="32" height="32">
        </div>
        <h3 class="doc-card-title">{section_title}</h3>
        <ul class="doc-card-preview">
          {preview_items}
        </ul>
        <span class="doc-card-count">{file_count} {_pluralize(file_count, lang)}</span>
      </a>''')

    cards_grid = '\n'.join(cards_html)

    return f'''<!DOCTYPE html>
<html lang="{lang}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="description" content="{description}">

  <title>{title}</title>

  <link rel="icon" type="image/svg+xml" href="../../assets/svg/logo-compact.svg">
  <link rel="stylesheet" href="../../css/styles.css">

  <style>
    .doc-index {{
      max-width: 1200px;
      margin: 0 auto;
      padding: var(--spacing-8);
    }}

    .doc-index-hero {{
      text-align: center;
      padding: var(--spacing-16) 0;
      background: linear-gradient(135deg, var(--color-primary-50), var(--color-bg));
      border-radius: var(--radius-2xl);
      margin-bottom: var(--spacing-12);
    }}

    [data-theme="dark"] .doc-index-hero {{
      background: linear-gradient(135deg, rgba(37, 99, 235, 0.1), var(--color-bg));
    }}

    .doc-index-hero h1 {{
      font-size: var(--font-size-4xl);
      margin-bottom: var(--spacing-4);
    }}

    .doc-index-hero p {{
      font-size: var(--font-size-xl);
      color: var(--color-text-muted);
    }}

    .doc-cards {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
      gap: var(--spacing-6);
    }}

    .doc-card {{
      display: block;
      padding: var(--spacing-6);
      background: var(--color-bg-card);
      border: 1px solid var(--color-border-light);
      border-radius: var(--radius-xl);
      text-decoration: none;
      color: var(--color-text);
      transition: all var(--transition-normal);
    }}

    .doc-card:hover {{
      border-color: var(--color-primary);
      box-shadow: var(--shadow-lg);
      transform: translateY(-2px);
    }}

    .doc-card-icon {{
      width: 48px;
      height: 48px;
      background: var(--color-primary-50);
      border-radius: var(--radius-lg);
      display: flex;
      align-items: center;
      justify-content: center;
      margin-bottom: var(--spacing-4);
    }}

    .doc-card-title {{
      font-size: var(--font-size-xl);
      margin-bottom: var(--spacing-3);
    }}

    .doc-card-preview {{
      list-style: none;
      padding: 0;
      margin: 0 0 var(--spacing-4) 0;
      font-size: var(--font-size-sm);
      color: var(--color-text-muted);
    }}

    .doc-card-preview li {{
      padding: var(--spacing-1) 0;
    }}

    .doc-card-count {{
      font-size: var(--font-size-xs);
      color: var(--color-text-muted);
      background: var(--color-bg-alt);
      padding: var(--spacing-1) var(--spacing-2);
      border-radius: var(--radius-sm);
    }}

    .lang-switcher {{
      display: flex;
      gap: var(--spacing-1);
    }}

    .lang-switcher a {{
      padding: var(--spacing-1) var(--spacing-3);
      border-radius: var(--radius-md);
      font-size: var(--font-size-sm);
      text-decoration: none;
      color: var(--color-text-muted);
      border: 1px solid var(--color-border);
    }}

    .lang-switcher a.active {{
      background: var(--color-primary);
      color: white;
      border-color: var(--color-primary);
    }}
  </style>
</head>
<body>
  <header class="header">
    <nav class="nav container">
      <a href="../../index.html" class="logo">
        <img src="../../assets/svg/logo.svg" alt="CodeGraph" width="160" height="40">
      </a>

      <ul class="nav-list">
        <li><a href="../../index.html#problems" class="nav-link">{ui['nav_problems']}</a></li>
        <li><a href="../../index.html#solution" class="nav-link">{ui['nav_solution']}</a></li>
        <li><a href="../../index.html#features" class="nav-link">{ui['nav_features']}</a></li>
        <li><a href="../../index.html#integrations" class="nav-link">{ui['nav_integrations']}</a></li>
        <li><a href="index.html" class="nav-link active">{ui['nav_docs']}</a></li>
        <li><a href="../../index.html#faq" class="nav-link">{ui['nav_faq']}</a></li>
      </ul>

      <div class="header-actions">
        <div class="lang-switcher">
          <a href="../en/index.html" class="{en_class}">EN</a>
          <a href="../ru/index.html" class="{ru_class}">RU</a>
        </div>
        <button class="theme-toggle" aria-label="{ui['toggle_theme']}">
          <svg class="icon-sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20">
            <circle cx="12" cy="12" r="5"/>
            <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
          </svg>
          <svg class="icon-moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20">
            <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
          </svg>
        </button>
        <a href="../../index.html#demo" class="btn btn-primary">{ui['nav_request_demo']}</a>
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
        <li><a href="../../index.html#problems" class="mobile-nav-link">{ui['nav_problems']}</a></li>
        <li><a href="../../index.html#solution" class="mobile-nav-link">{ui['nav_solution']}</a></li>
        <li><a href="../../index.html#features" class="mobile-nav-link">{ui['nav_features']}</a></li>
        <li><a href="../../index.html#integrations" class="mobile-nav-link">{ui['nav_integrations']}</a></li>
        <li><a href="index.html" class="mobile-nav-link">{ui['nav_docs']}</a></li>
        <li><a href="../../index.html#faq" class="mobile-nav-link">{ui['nav_faq']}</a></li>
        <li><a href="../../index.html#demo" class="btn btn-primary mobile-nav-demo-btn">{ui['nav_request_demo']}</a></li>
      </ul>
    </nav>
  </header>

  <main class="doc-index">
    <div class="doc-index-hero">
      <h1>{welcome}</h1>
      <p>{welcome_desc}</p>
    </div>

    <div class="doc-cards">
      {cards_grid}
    </div>
  </main>

  <footer class="footer">
    <div class="container">
      <div class="footer-content">
        <div class="footer-brand">
          <img src="../../assets/svg/logo.svg" alt="CodeGraph" width="160" height="40">
          <p>{ui['footer_tagline']}</p>
        </div>
        <div class="footer-links">
          <div class="footer-links-group">
            <h4>{ui['footer_product']}</h4>
            <ul class="footer-links-list">
              <li><a href="../../index.html#features" class="footer-link">{ui['nav_features']}</a></li>
              <li><a href="../../index.html#integrations" class="footer-link">{ui['nav_integrations']}</a></li>
              <li><a href="../../index.html#faq" class="footer-link">{ui['nav_faq']}</a></li>
            </ul>
          </div>
          <div class="footer-links-group">
            <h4>{ui['footer_docs']}</h4>
            <ul class="footer-links-list">
              <li><a href="getting-started/index.html" class="footer-link">{ui['footer_getting_started']}</a></li>
              <li><a href="guides/index.html" class="footer-link">{ui['footer_guides']}</a></li>
              <li><a href="api/index.html" class="footer-link">{ui['footer_api']}</a></li>
              <li><a href="enterprise/index.html" class="footer-link">{ui['footer_enterprise']}</a></li>
            </ul>
          </div>
          <div class="footer-links-group">
            <h4>{ui['footer_resources']}</h4>
            <ul class="footer-links-list">
              <li><a href="../../whitepaper.html" class="footer-link">{ui['footer_whitepaper']}</a></li>
            </ul>
          </div>
          <div class="footer-links-group">
            <h4>{ui['footer_contacts']}</h4>
            <ul class="footer-links-list">
              <li><a href="mailto:hello@codegraph.ru" class="footer-link">hello@codegraph.ru</a></li>
              <li><a href="https://t.me/codegraph" class="footer-link">Telegram</a></li>
              <li><a href="https://github.com/codegraph" class="footer-link">GitHub</a></li>
            </ul>
          </div>
        </div>
      </div>
      <div class="footer-bottom">
        <p>&copy; {date.today().year} CodeGraph. {ui['rights_reserved']}</p>
      </div>
    </div>
  </footer>

  <script src="../../js/main.js"></script>
</body>
</html>
'''


def generate_section_index(
    section_id: str,
    section_title: str,
    files: List[Dict],
    lang: str,
    sidebar_html: str,
    prev_section: Dict = None,
    next_section: Dict = None,
) -> str:
    """
    Generate section index page.

    Args:
        section_id: Section identifier
        section_title: Localized section title
        files: List of file info dicts
        lang: Language code
        sidebar_html: Pre-rendered sidebar HTML
        prev_section: Previous section dict with 'id' and 'title' keys
        next_section: Next section dict with 'id' and 'title' keys

    Returns:
        Complete HTML for section index
    """
    ui = UI_STRINGS.get(lang, UI_STRINGS['en'])

    # Language switcher classes
    en_class = "active" if lang == 'en' else ""
    ru_class = "active" if lang == 'ru' else ""

    # Build file list
    file_items = []
    for f in files:
        if f['slug'].lower() in ('readme', 'index'):
            continue

        # Use Russian title if available for RU language
        if lang == 'ru' and 'title_ru' in f:
            title = f['title_ru']
        else:
            title = f.get('title', f['slug'])
        description = f.get('description', '')

        file_items.append(f'''
        <li>
          <a href="{f['slug']}.html">
            <strong>{title}</strong>
            {f'<p>{description}</p>' if description else ''}
          </a>
        </li>''')

    file_list = '\n'.join(file_items) if file_items else '<li><em>No documents yet</em></li>'

    # Generate section navigation
    section_nav_parts = []
    if prev_section or next_section:
        section_nav_parts.append('<nav class="doc-page-nav">')
        if prev_section:
            section_nav_parts.append(f'''
      <a href="../{prev_section['id']}/index.html" class="doc-page-nav-prev">
        <span class="doc-page-nav-label">{ui['nav_prev']}</span>
        <span class="doc-page-nav-title">{prev_section['title']}</span>
      </a>''')
        else:
            section_nav_parts.append('      <span></span>')

        if next_section:
            section_nav_parts.append(f'''
      <a href="../{next_section['id']}/index.html" class="doc-page-nav-next">
        <span class="doc-page-nav-label">{ui['nav_next']}</span>
        <span class="doc-page-nav-title">{next_section['title']}</span>
      </a>''')
        section_nav_parts.append('    </nav>')

    section_nav_html = '\n'.join(section_nav_parts)

    return f'''<!DOCTYPE html>
<html lang="{lang}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{section_title} - CodeGraph Documentation</title>
  <link rel="icon" type="image/svg+xml" href="{ASSETS_PATH}/svg/logo-compact.svg">
  <link rel="stylesheet" href="{CSS_PATH}">

  <style>
    .doc-layout {{ display: flex; min-height: calc(100vh - 72px); }}
    .doc-sidebar {{ position: sticky; top: 72px; width: 280px; height: calc(100vh - 72px);
      padding: var(--spacing-6); background: var(--color-bg);
      border-right: 1px solid var(--color-border-light); overflow-y: auto; flex-shrink: 0; }}
    .doc-sidebar-section {{ margin-bottom: var(--spacing-6); }}
    .doc-sidebar-title {{ font-size: var(--font-size-xs); font-weight: var(--font-weight-semibold);
      text-transform: uppercase; letter-spacing: 0.05em; color: var(--color-text-muted); margin-bottom: var(--spacing-2); }}
    .doc-sidebar-nav {{ list-style: none; padding: 0; margin: 0; }}
    .doc-sidebar-nav a {{ display: block; padding: var(--spacing-2) var(--spacing-3);
      color: var(--color-text); text-decoration: none; border-radius: var(--radius-md);
      font-size: var(--font-size-sm); transition: all var(--transition-fast); }}
    .doc-sidebar-nav a:hover {{ background: var(--color-bg-alt); color: var(--color-primary); }}
    .doc-sidebar-nav a.active {{ background: var(--color-primary-50); color: var(--color-primary);
      font-weight: var(--font-weight-medium); }}
    .doc-main {{ flex: 1; max-width: 900px; margin: 0 auto; padding: var(--spacing-8); }}
    .doc-hero {{ text-align: center; padding: var(--spacing-12) 0;
      background: linear-gradient(135deg, var(--color-primary-50), var(--color-bg));
      border-radius: var(--radius-2xl); margin-bottom: var(--spacing-8); }}
    [data-theme="dark"] .doc-hero {{ background: linear-gradient(135deg, rgba(37, 99, 235, 0.1), var(--color-bg)); }}
    .doc-content {{ background: var(--color-bg-card); border-radius: var(--radius-xl);
      padding: var(--spacing-8); border: 1px solid var(--color-border-light); }}
    .doc-content ul {{ list-style: none; padding: 0; }}
    .doc-content li {{ margin: var(--spacing-3) 0; }}
    .doc-content li a {{ display: block; padding: var(--spacing-4); background: var(--color-bg-alt);
      border-radius: var(--radius-lg); text-decoration: none; color: var(--color-text);
      transition: all var(--transition-fast); }}
    .doc-content li a:hover {{ background: var(--color-primary-50); }}
    .doc-content li strong {{ display: block; font-size: var(--font-size-lg); margin-bottom: var(--spacing-1); }}
    .doc-content li p {{ margin: 0; font-size: var(--font-size-sm); color: var(--color-text-muted); }}
    .lang-switcher {{ display: flex; gap: var(--spacing-1); }}
    .lang-switcher a {{ padding: var(--spacing-1) var(--spacing-3); border-radius: var(--radius-md);
      font-size: var(--font-size-sm); text-decoration: none; color: var(--color-text-muted);
      border: 1px solid var(--color-border); }}
    .lang-switcher a.active {{ background: var(--color-primary); color: white; border-color: var(--color-primary); }}
    @media (max-width: 1024px) {{ .doc-sidebar {{ display: none; }} }}
  </style>
</head>
<body>
  <header class="header">
    <nav class="nav container">
      <a href="../../../index.html" class="logo">
        <img src="{ASSETS_PATH}/svg/logo.svg" alt="CodeGraph" width="160" height="40">
      </a>
      <ul class="nav-list">
        <li><a href="../../../index.html#problems" class="nav-link">{ui['nav_problems']}</a></li>
        <li><a href="../../../index.html#solution" class="nav-link">{ui['nav_solution']}</a></li>
        <li><a href="../../../index.html#features" class="nav-link">{ui['nav_features']}</a></li>
        <li><a href="../../../index.html#integrations" class="nav-link">{ui['nav_integrations']}</a></li>
        <li><a href="../index.html" class="nav-link active">{ui['nav_docs']}</a></li>
        <li><a href="../../../index.html#faq" class="nav-link">{ui['nav_faq']}</a></li>
      </ul>
      <div class="header-actions">
        <div class="lang-switcher">
          <a href="../../en/{section_id}/index.html" class="{en_class}">EN</a>
          <a href="../../ru/{section_id}/index.html" class="{ru_class}">RU</a>
        </div>
        <button class="theme-toggle" aria-label="{ui['toggle_theme']}">
          <svg class="icon-sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20">
            <circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
          </svg>
          <svg class="icon-moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20">
            <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
          </svg>
        </button>
        <a href="../../../index.html#demo" class="btn btn-primary">{ui['nav_request_demo']}</a>
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
        <li><a href="../../../index.html#problems" class="mobile-nav-link">{ui['nav_problems']}</a></li>
        <li><a href="../../../index.html#solution" class="mobile-nav-link">{ui['nav_solution']}</a></li>
        <li><a href="../../../index.html#features" class="mobile-nav-link">{ui['nav_features']}</a></li>
        <li><a href="../../../index.html#integrations" class="mobile-nav-link">{ui['nav_integrations']}</a></li>
        <li><a href="../index.html" class="mobile-nav-link">{ui['nav_docs']}</a></li>
        <li><a href="../../../index.html#faq" class="mobile-nav-link">{ui['nav_faq']}</a></li>
        <li><a href="../../../index.html#demo" class="btn btn-primary mobile-nav-demo-btn">{ui['nav_request_demo']}</a></li>
      </ul>
    </nav>
  </header>

  <div class="doc-layout">
    <aside class="doc-sidebar">
      {sidebar_html}
    </aside>

    <main class="doc-main">
      <div class="doc-hero">
        <h1>{section_title}</h1>
      </div>

      <div class="doc-content">
        <ul>
          {file_list}
        </ul>
      </div>

      {section_nav_html}
    </main>
  </div>

  <footer class="footer">
    <div class="container">
      <div class="footer-content">
        <div class="footer-brand">
          <img src="{ASSETS_PATH}/svg/logo.svg" alt="CodeGraph" width="160" height="40">
          <p>{ui['footer_tagline']}</p>
        </div>
        <div class="footer-links">
          <div class="footer-links-group">
            <h4>{ui['footer_product']}</h4>
            <ul class="footer-links-list">
              <li><a href="../../../index.html#features" class="footer-link">{ui['nav_features']}</a></li>
              <li><a href="../../../index.html#integrations" class="footer-link">{ui['nav_integrations']}</a></li>
              <li><a href="../../../index.html#faq" class="footer-link">{ui['nav_faq']}</a></li>
            </ul>
          </div>
          <div class="footer-links-group">
            <h4>{ui['footer_docs']}</h4>
            <ul class="footer-links-list">
              <li><a href="../getting-started/index.html" class="footer-link">{ui['footer_getting_started']}</a></li>
              <li><a href="../guides/index.html" class="footer-link">{ui['footer_guides']}</a></li>
              <li><a href="../api/index.html" class="footer-link">{ui['footer_api']}</a></li>
              <li><a href="../enterprise/index.html" class="footer-link">{ui['footer_enterprise']}</a></li>
            </ul>
          </div>
          <div class="footer-links-group">
            <h4>{ui['footer_resources']}</h4>
            <ul class="footer-links-list">
              <li><a href="../../../whitepaper.html" class="footer-link">{ui['footer_whitepaper']}</a></li>
            </ul>
          </div>
          <div class="footer-links-group">
            <h4>{ui['footer_contacts']}</h4>
            <ul class="footer-links-list">
              <li><a href="mailto:hello@codegraph.ru" class="footer-link">hello@codegraph.ru</a></li>
              <li><a href="https://t.me/codegraph" class="footer-link">Telegram</a></li>
              <li><a href="https://github.com/codegraph" class="footer-link">GitHub</a></li>
            </ul>
          </div>
        </div>
      </div>
      <div class="footer-bottom">
        <p>&copy; {date.today().year} CodeGraph. {ui['rights_reserved']}</p>
      </div>
    </div>
  </footer>

  <script src="{JS_PATH}"></script>
</body>
</html>
'''


def _pluralize(count: int, lang: str) -> str:
    """Get pluralized word for 'documents'."""
    if lang == 'ru':
        if count % 10 == 1 and count % 100 != 11:
            return "документ"
        elif 2 <= count % 10 <= 4 and (count % 100 < 10 or count % 100 >= 20):
            return "документа"
        else:
            return "документов"
    else:
        return "document" if count == 1 else "documents"
