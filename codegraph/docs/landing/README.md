# Landing Page Assets

> Web assets for the CodeGraph landing page.

## Structure

```
landing/
├── index.html         # Main landing page
├── whitepaper.html    # Technical whitepaper
├── robots.txt         # Search engine directives
├── sitemap.xml        # XML sitemap
├── css/
│   └── styles.css     # Main stylesheet
├── js/
│   └── main.js        # JavaScript functionality
└── assets/svg/        # SVG graphics
    ├── logo.svg
    ├── logo-compact.svg
    ├── diagram-architecture.svg
    ├── diagram-pipeline.svg
    └── icon-*.svg     # Feature icons
```

## Usage

These assets are for the public-facing website. To preview locally:

```bash
cd docs/landing
python -m http.server 8000
```

Then open http://localhost:8000 in your browser.

## Design Guidelines

- Primary color: `#0366d6` (blue)
- Font: System font stack
- Icons: Monochrome SVG with fill color inheritance
