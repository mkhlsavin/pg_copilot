# PostgreSQL Books QA Dataset Generator - Documentation

## Project Summary
Generates 3,318 QA pairs from PostgreSQL technical books for RAG evaluation.

## Fixed Issues (2025-10-03)
1. PDF extraction corrupted → Using web book only  
2. Re-chunked with clean data → 1,659 chunks from 1,651 items
3. Fixed chunk identifiers → Uses chapter/section names  
4. Regeneration ready → Run: python generate_qa_from_chunks.py --qa-per-chunk 2

## Key Files
- config.py: Configuration
- web_book_scraper.py: Web scraping  
- content_chunker.py: Semantic chunking
- generate_qa_from_chunks.py: QA generation (RECOMMENDED)
- dataset_builder.py: Final assembly

## Quick Start
python web_book_scraper.py
python content_chunker.py
python generate_qa_from_chunks.py --qa-per-chunk 2

## Performance
Total time: ~16 hours for 3,318 QA pairs
Hardware: RTX 3090, 24GB VRAM

See README_old.md for original documentation.

