# TUI Module

Rich terminal user interface providing interactive access to CodeGraph with themes, scenario panels, and real-time progress tracking.

## Overview

```
src/tui/
├── app.py               # Main TUI application
├── components/          # UI components
│   ├── chat.py          # Chat interface
│   ├── scenarios.py     # Scenario panel
│   ├── progress.py      # Progress indicators
│   └── output.py        # Output formatting
├── themes/              # Color themes
│   ├── default.py
│   ├── dark.py
│   └── light.py
├── session.py           # Session management
└── __init__.py          # Module exports
```

## Running the TUI

```bash
# Start TUI
python -m src.tui.app

# With specific theme
python -m src.tui.app --theme dark

# With specific project
python -m src.tui.app --project postgresql-17
```

## Features

### Interactive Chat
- Natural language queries
- Streaming responses
- Query history (up/down arrows)
- Auto-completion

### Scenario Panel
- Quick access to 16 scenarios
- Example queries per scenario
- Keyboard shortcuts

### Progress Tracking
- Real-time progress bars
- Stage-by-stage updates
- Error highlighting

### Themes
- Default (balanced)
- Dark mode
- Light mode
- Custom themes

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Ctrl+C` | Cancel current query |
| `Ctrl+D` | Exit TUI |
| `Tab` | Switch panels |
| `↑/↓` | Navigate history |
| `F1-F16` | Quick scenario select |
| `Ctrl+L` | Clear screen |

## Usage

```python
from src.tui.app import TUIApp

# Start application
app = TUIApp()
app.run()
```

## Configuration

```yaml
tui:
  theme: default
  history_size: 100
  show_confidence: true
  show_evidence: true
  streaming: true
```

## Session Persistence

Sessions are saved to `~/.codegraph/sessions/`:
- Query history
- Active project
- Theme preferences

## See Also

- `/src/cli/` - Command-line interface
- `/src/api/` - REST API
