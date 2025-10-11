# Quick Start Guide

**Status:** ✅ System is fully tested and ready for production use.

## Prerequisites

All dependencies are already installed. The system has been tested with:
- PostgreSQL mailing list archives at postgresql.org
- Qwen3-32B LLM for QA generation
- PostgreSQL 17.6 source code

## Quick Test (5 minutes)

Verify the system works with sample data:

```bash
# 1. Generate 49 sample emails in 9 threads
python generate_sample_data.py

# 2. Run complete pipeline (takes ~2-3 minutes)
python main.py --parse --cluster --map-source --generate-qa --max-clusters 1 --build-dataset

# 3. Check output
cat output/dataset_report.json
```

**Expected output:** 5 QA pairs about WAL/Replication in `output/pg_copilot_qa_dataset.jsonl`

## Production Pipeline (2022-2025 archives)

The scraper is configured for postgresql.org with **10.8 emails/second** performance:

```bash
# Option 1: Full pipeline in one command
python main.py --all

# Option 2: Step-by-step (recommended for monitoring)
python main.py --scrape                    # 7-8 hours for 2022-2025 (~300k emails)
python main.py --parse --cluster           # 10-15 minutes
python main.py --map-source                # 5-10 minutes
python main.py --generate-qa               # 4-8 hours (per year)
python main.py --build-dataset             # 1-2 minutes
```

**Performance:**
- **Scraping rate**: 10.8 emails/second (5 concurrent connections)
- **Single month**: ~10 minutes (~2,500 messages)
- **Full year**: ~2 hours (~80,000 messages)
- **2022-2025 (4 years)**: ~7-8 hours (~300,000 messages)

**Expected output:** 4,000-7,000 QA pairs about PostgreSQL 17.6 internals

### Resume from Checkpoint

The scraper automatically saves progress after each month:

```bash
# Continues from last completed archive
python main.py --scrape

# Start fresh (ignore checkpoint)
python main.py --scrape --no-checkpoint

# Check current progress
ls -lh data/scraper_checkpoint.json
```

### Configuration

The scraper is configured in `config.py`:
```python
MAILING_LIST_URL = "https://www.postgresql.org/list/pgsql-hackers"
START_YEAR = 2022
END_YEAR = 2025

# Performance tuning
RATE_LIMIT_DELAY = 0.1  # Seconds between requests (10 req/sec)
CONCURRENT_REQUESTS = 5  # Parallel message fetches
```

HTML selectors are configured for postgresql.org:
- Archive pages: Links with `/message-id/` pattern
- Day pagination: Links with `/since/YYYYMMDDHHMMSS/` pattern
- Message pages: Header table + `div.message-content` for body

## Output

Final dataset will be in:
- `output/pg_copilot_qa_dataset.jsonl` - QA pairs
- `output/dataset_report.json` - Statistics
- `output/README.md` - Dataset documentation

## Troubleshooting

### GPU Out of Memory
Edit `config.py`:
```python
N_CTX = 4096  # Reduce from 8192
N_BATCH = 256  # Reduce from 512
```

### HDBSCAN Warning
```
WARNING: HDBSCAN not available, using KMeans only
```
- Normal on Windows
- Automatically falls back to KMeans
- No action needed

### Empty Response from LLM
If QA generation returns no results:
- The system already handles `<think>` reasoning tokens
- Check GPU memory availability
- Reduce `GENERATION_MAX_TOKENS` in config.py

### Thread Parsing Issues
If `processed_threads.json` shows 0 threads:
- Fixed: message_id lookup bug (already patched)
- Sample data should produce 10 threads

## Testing & Validation

See [TESTING.md](TESTING.md) for:
- Complete test results
- Bug fixes applied
- Sample vs. real data comparisons

## Documentation

- **[README.md](README.md)** - Complete system documentation
- **[STATUS.md](STATUS.md)** - Testing checklist and status
- **[TESTING.md](TESTING.md)** - Detailed test results
- **[docs/](docs/)** - Module-specific documentation
