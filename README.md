# DEA AI Research Intelligence

[![GitHub Actions Status](https://github.com/pbtsvinaysukhesh/dea-genai-agent/workflows/Tests/badge.svg)](https://github.com/pbtsvinaysukhesh/dea-genai-agent/actions)
[![CodeQL](https://github.com/pbtsvinaysukhesh/dea-genai-agent/workflows/CodeQL/badge.svg)](https://github.com/pbtsvinaysukhesh/dea-genai-agent/actions)

Daily AI research automation that collects sources, scores relevance, stores source context in Qdrant, and generates email, PDF, PPTX, podcast, transcript, and summary outputs.

## What It Does

1. Collects research sources from arXiv, RSS feeds, GitHub, and crawled pages
2. Deep-fetches content with Playwright when available
3. Removes duplicates with vector similarity and history tracking
4. Scores and shortlists the top findings
5. Generates multi-format reports from one shared report bundle
6. Emails the deliverables with clickable source links and attachments

## Active Pipeline

The current runtime path is centered on:

- `main.py`
- `src/collector.py`
- `src/deep_scraper.py`
- `src/qdrant_vector_store.py`
- `src/multi_format_orchestrator.py`
- `src/multiformat_integration.py`
- `src/report_bundle.py`

## Technology Stack

```text
LLMs: Groq, Gemini, Ollama fallback
Search: Qdrant semantic similarity + metadata scoring
Scraping: Playwright
Reports: ReportLab, python-pptx, gTTS/pydub
Backend: FastAPI + WebSocket
Frontend: HTML/JS SPA
CI/CD: GitHub Actions
```

## Local Run

```bash
git clone https://github.com/pbtsvinaysukhesh/dea-genai-agent
cd dea-genai-agent
pip install -r requirements.txt
python main.py
```

## Configuration

Main config lives in `config/config.yaml`.

Example:

```yaml
system:
  relevance_threshold: 60
  use_vectors: true

sources:
  arxiv_queries: [...]
  rss_feeds: [...]
  github:
    enabled: true

email:
  recipients: ["you@email.com"]
```

## Outputs

The pipeline generates:

- Email HTML digest
- PDF report with clickable source appendix
- PowerPoint deck with source slides
- Podcast audio with transcript and embedded source metadata
- Summary text and JSON
- Source index JSON for full fetched URL traceability

## Source Traceability

Every fetched URL is preserved in the shared report bundle with:

- original source URL
- source platform/type
- fetch timestamp
- content excerpt
- metadata needed for PDF/email appendix rendering

This data powers clickable links in the email and PDF outputs.

## Repository Cleanup

Legacy and debug-only assets have been archived instead of deleted:

- `dump/unused_code/`
- `dump/unused_tests/`

This keeps the active repo surface smaller while preserving older experiments and compatibility code for reference.

## Testing

Current focused tests include:

- `tests/test_backup_system.py`
- `tests/test_report_bundle.py`

## Dashboard

Dashboard app remains under `Dashboard/` with FastAPI backend and frontend assets.

## Status

Production-oriented active pipeline with archived legacy modules kept under `dump/`.
