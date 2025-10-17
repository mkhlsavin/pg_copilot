# Streaming Progress Output - Implementation Guide

## Overview

The RAG-CPGQL workflow now supports **real-time streaming progress output** using the Rich library. This enhancement provides live visual feedback during workflow execution, making it easier to monitor long-running operations and debug issues.

## Features

### Visual Enhancements
- **Real-time agent status updates** with emoji indicators (🔍 Analyzer, 📚 Retriever, ⚡ Generator, etc.)
- **Colorized console output** (green for success, red for errors, blue for in-progress)
- **Live metrics display** showing key performance indicators for each agent
- **Progress summary table** at completion with timing and status for all agents
- **TTY-friendly output** with automatic fallback to plain text for non-TTY environments

### Architecture
- **Backward compatible**: Existing code continues to work with `verbose=True`
- **Optional streaming mode**: Enable with `streaming=True` parameter
- **Zero overhead when disabled**: Progress tracker only activates when requested
- **Non-serialized state**: Tracker attached to workflow state but not persisted

## Usage

### Basic Streaming Mode

```python
from src.workflow.langgraph_workflow import run_workflow

# Enable streaming progress
result = run_workflow(
    question="How does PostgreSQL handle MVCC?",
    verbose=False,   # Disable legacy mode
    streaming=True   # Enable Rich streaming
)
```

### Legacy Verbose Mode (Backward Compatible)

```python
# Old code still works without changes
result = run_workflow(
    question="How does PostgreSQL handle MVCC?",
    verbose=True,
    streaming=False  # Default
)
```

### Silent Mode

```python
# No progress output
result = run_workflow(
    question="How does PostgreSQL handle MVCC?",
    verbose=False,
    streaming=False
)
```

## Example Output

### Streaming Mode Output

```
================================================================================
╭────────────────────────────────────────────────────────────────────────────╮
│ RAG-CPGQL LangGraph Workflow                                               │
│                                                                            │
│ Question: How does PostgreSQL handle MVCC?                                 │
╰────────────────────────────────────────────────────────────────────────────╯

🔍 ANALYZER starting...
🔍 ANALYZER completed in 0.12s │ domain=memory │ intent=explain-concept │ complexity=medium

📚 RETRIEVER starting...
📚 RETRIEVER completed in 0.45s │ qa_count=3 │ cpgql_count=5 │ avg_similarity=0.782

🏷️  ENRICHMENT starting...
🏷️  ENRICHMENT completed in 0.08s │ tag_count=12 │ coverage=0.44

⚡ GENERATOR starting...
⚡ GENERATOR completed in 3.72s │ valid=True │ time=3.72

✓ VALIDATOR starting...
✓ VALIDATOR completed in 0.01s │ valid=True

▶️  EXECUTOR starting...
▶️  EXECUTOR completed in 0.52s │ success=True │ time=0.52

💬 INTERPRETER starting...
💬 INTERPRETER completed in 0.03s │ confidence=0.8

📊 EVALUATOR starting...
📊 EVALUATOR completed in 1.24s │ overall_score=0.823

================================================================================
┏━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Agent           ┃ Status     ┃     Time ┃ Key Metrics                 ┃
┡━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ 🔍 Analyzer     │ ✓ Complete │    0.12s │ domain=memory, intent=...   │
│ 📚 Retriever    │ ✓ Complete │    0.45s │ qa_count=3, cpgql_count=5   │
│ 🏷️  Enrichment  │ ✓ Complete │    0.08s │ tag_count=12, coverage=0.44 │
│ ⚡ Generator    │ ✓ Complete │    3.72s │ valid=True, time=3.72       │
│ ✓ Validator     │ ✓ Complete │    0.01s │ valid=True                  │
│ ▶️  Executor     │ ✓ Complete │    0.52s │ success=True, time=0.52     │
│ 💬 Interpreter  │ ✓ Complete │    0.03s │ confidence=0.8              │
│ 📊 Evaluator    │ ✓ Complete │    1.24s │ overall_score=0.823         │
└─────────────────┴────────────┴──────────┴─────────────────────────────┘

Final Results:
  Query Valid: True
  Execution: SUCCESS
  RAGAS Score: 0.823
  Total Time: 6.17s

================================================================================
```

## Implementation Details

### Module Structure

```
src/workflow/
├── langgraph_workflow.py      # Main workflow with tracker integration
└── streaming_progress.py      # ProgressTracker class and utilities
```

### Key Components

#### ProgressTracker Class (src/workflow/streaming_progress.py)

```python
class ProgressTracker:
    """Real-time progress tracker for LangGraph workflow."""

    def __init__(self, enabled: bool = True, use_rich: bool = True):
        """Initialize tracker with optional Rich console support."""

    def start_workflow(self, question: str):
        """Begin tracking a new workflow execution."""

    def start_agent(self, agent_name: str):
        """Mark an agent as started."""

    def complete_agent(self, agent_name: str, metrics: Optional[Dict] = None):
        """Mark an agent as completed with optional metrics."""

    def fail_agent(self, agent_name: str, error: str):
        """Mark an agent as failed."""

    def complete_workflow(self, final_state: Dict):
        """Complete workflow and show final summary."""
```

#### Agent Integration Pattern

Each agent node follows this pattern:

```python
def agent_node(state: RAGCPGQLState) -> RAGCPGQLState:
    """Agent implementation."""
    tracker = state.get("_progress_tracker")
    if tracker:
        tracker.start_agent("agent_name")

    try:
        # Agent work here
        ...

        if tracker:
            tracker.complete_agent("agent_name", {"metric": value})

    except Exception as e:
        if tracker:
            tracker.fail_agent("agent_name", str(e))
        raise

    return state
```

### State Schema Update

```python
class RAGCPGQLState(TypedDict):
    # ... existing fields ...

    # Progress tracking (not serialized)
    _progress_tracker: Optional[ProgressTracker]
```

## Testing

### Manual Testing

```bash
# Activate environment
conda activate llama.cpp

# Run test suite
python test_streaming_progress.py
```

### Integration with Existing Tests

Update existing test scripts to use streaming mode:

```python
# experiments/test_langgraph_workflow.py
result = run_workflow(
    question=question,
    verbose=False,
    streaming=True  # Enable streaming for better visibility
)
```

## Dependencies

- **Rich >= 13.7.0**: Added to `requirements.txt`
- **Python >= 3.11**: Required for TypedDict and other features
- **TTY support**: Streaming mode automatically falls back to plain text in non-TTY environments

## Performance Impact

- **Minimal overhead**: Progress tracking adds < 1ms per agent
- **No serialization cost**: Tracker is not persisted to workflow state
- **Lazy initialization**: Components only loaded when streaming is enabled
- **Memory efficient**: Uses shared singleton pattern for reusable components

## Migration Guide

### For Existing Code

No changes required! Existing code with `verbose=True` continues to work:

```python
# This still works exactly as before
result = run_workflow(question, verbose=True)
```

### For New Code

Use streaming mode for better visibility:

```python
# New recommended approach
result = run_workflow(question, streaming=True)
```

### For Batch Processing

Disable progress output to avoid clutter:

```python
# Silent mode for large batch runs
results = []
for question in questions:
    result = run_workflow(question, verbose=False, streaming=False)
    results.append(result)
```

## Troubleshooting

### Rich Library Not Found

```bash
# Install Rich library
conda activate llama.cpp
pip install rich>=13.7.0
```

### Colors Not Displaying

- **Issue**: Running in non-TTY environment (e.g., redirected to file)
- **Solution**: Streaming mode automatically falls back to plain text
- **Force colors**: Set `FORCE_COLOR=1` environment variable

### Performance Issues

- **Issue**: Progress output slows down workflow
- **Solution**: Disable streaming for production runs: `streaming=False`

## Future Enhancements

Potential improvements for future iterations:

1. **LangSmith Integration**: Send progress events to LangSmith for observability
2. **Web Dashboard**: Real-time progress via WebSocket for browser-based monitoring
3. **Custom Themes**: Configurable color schemes and emoji sets
4. **Export Options**: Save progress logs to JSON/HTML for analysis
5. **Streaming Callbacks**: Hook into LangGraph's callback system for more granular updates

## Related Documentation

- [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md) - Overall project roadmap
- [README.md](./README.MD) - Project overview and setup
- [LANGGRAPH_ARCHITECTURE.md](./LANGGRAPH_ARCHITECTURE.md) - Workflow architecture details

## Changelog

### v1.0.0 (2025-10-16)
- Initial implementation of streaming progress tracker
- Added Rich-based console output with colorization
- Integrated with all 9 LangGraph workflow agents
- Backward compatibility with legacy verbose mode
- Created test suite and documentation
