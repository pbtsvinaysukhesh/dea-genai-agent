# README - On-Device AI Research Intelligence Agent

**A comprehensive AI research pipeline for discovering, analyzing, and delivering insights on on-device AI, memory optimization, and edge computing.**

---

## Overview

This project combines:
- **Multi-source data collection** (arXiv, RSS feeds, GitHub, Google Scholar)
- **LLM-powered analysis** (Groq, Ollama, Gemini) with automatic fallback
- **Hybrid RAG system** (BM25 + semantic search + MMR ranking)
- **Multi-format reports** (Email HTML, PDF, PowerPoint, Podcast, Transcript)
- **Human-in-the-loop review** (HITL validation and approval workflow)
- **Dashboard interface** (FastAPI backend + Single-Page App frontend)
- **GitHub Actions automation** (daily scheduled execution, no infrastructure required)

---

## Quick Start

### 1. Local Development (with Ollama)

```bash
# Clone and setup
git clone https://github.com/pbtsvinaysukhesh/dea-genai-agent.git
cd dea-genai-agent

# Copy environment template
cp .env.example .env
# Edit .env with your API keys:
# - GOOGLE_API_KEY (from GCP)
# - GROQ_API_KEY (from Groq Console)
# - SMTP_* (for email delivery)

# Start with Docker Compose
docker-compose up
# This starts:
# - Ollama (local LLM, optional)
# - PostgreSQL (data storage, if configured)
# - FastAPI backend (port 8000)
```

### 2. GitHub Actions Only (No Local Setup)

```bash
# 1. Push code to GitHub (already done)
# 2. Add GitHub Secrets (Settings → Secrets and variables → Actions):
#    - GROQ_API_KEY
#    - GOOGLE_API_KEY
#    - SMTP_SERVER
#    - SMTP_PORT
#    - SMTP_USER
#    - SMTP_PASSWORD
#    - ENABLE_OLLAMA="false"

# 3. Scheduled execution happens daily at 9 AM UTC
# 4. Or manually trigger: Actions → "Scheduled AI Pipeline" → "Run workflow"
```

### 3. Dashboard Access

```
Frontend: http://localhost:3000 (if running locally)
Backend API: http://localhost:8000/docs (Swagger docs)
```

---

## Architecture

### Data Pipeline Flow

```
Sources (arXiv, RSS, GitHub)
  ↓
Article Collection & Deduplication
  ↓
Relevance Judge (keyword + LLM filter)
  ↓
Multi-AI Analysis (Groq → Ollama → Gemini with fallback)
  ↓
Quality Verification (AI Council consensus)
  ↓
Knowledge Graph & Vector Database
  ↓
→ HITL Review (Human approval)
→ Multi-Format Report Generation
  ├─ Email HTML (6+ papers)
  ├─ PDF (professional layout)
  ├─ PowerPoint (8 slides)
  ├─ Podcast (MP3 audio)
  ├─ Transcript (text version)
  └─ Summary (quick reference)
↓
Email Delivery with Attachments
↓
Results Archive
```

### Technology Stack

| Layer | Technology |
|-------|-----------|
| **API** | FastAPI, Pydantic, WebSocket |
| **Frontend** | HTML5 SPA, vanilla JS (no frameworks) |
| **LLM** | Groq (primary), Ollama (local), Gemini (fallback) |
| **Embeddings** | Sentence Transformers (Gemma-300m, 768 dims) |
| **Search** | BM25 (keyword) + Semantic (vector) + MMR (diversity) |
| **Knowledge** | Qdrant vector database + in-memory graph |
| **Reports** | ReportLab (PDF), python-pptx (PPT), gTTS (audio) |
| **Deployment** | Docker, GitHub Actions (free), self-hosted |
| **Email** | SMTP (Gmail, Outlook, custom servers) |

---

## Environment Variables

### Required (for GitHub Actions)
```env
GROQ_API_KEY=gsk_...              # Groq API key (fast LLM)
GOOGLE_API_KEY=AIza...            # Google/Gemini API key
SMTP_SERVER=smtp.gmail.com        # Email server
SMTP_PORT=587                     # SMTP port (TLS)
SMTP_USER=your-email@gmail.com    # Email address
SMTP_PASSWORD=...                 # App-specific password
```

### Optional (for advanced features)
```env
ENABLE_OLLAMA=true                # Use local Ollama (default: true)
OLLAMA_URL=http://localhost:11434 # Ollama endpoint
ENABLE_HITL=true                  # Manual review workflow
LOG_LEVEL=INFO                    # Logging verbosity
```

### Creating API Keys

**Google API Key:**
1. Go to [GCP Console](https://console.cloud.google.com)
2. Create project → APIs & Services → Credentials
3. Create API key → Copy to `GOOGLE_API_KEY`

**Groq API Key:**
1. Sign up at [Groq Console](https://console.groq.com)
2. Go to API keys → Create key → Copy to `GROQ_API_KEY`

**Gmail App Password:**
1. Enable 2FA on Gmail account
2. Go to [App Passwords](https://myaccount.google.com/apppasswords)
3. Generate password for "Mail" → Copy to `SMTP_PASSWORD`

---

## Features

### ✅ Multi-Provider LLM Support

Automatic fallback chain: Groq → Ollama → Gemini
- **Groq** (primary): Fast inference, no rate limits in free tier
- **Ollama** (local): Option for complete privacy, runs offline
- **Gemini** (fallback): When Groq/Ollama unavailable

### ✅ Hybrid RAG Search

Combines three techniques for relevance:
1. **BM25** - Keyword-based matching (fast)
2. **Semantic** - Vector similarity (accurate)
3. **MMR** - Maximum Marginal Relevance (diverse results)

### ✅ Multi-Format Report Generation

Generate 6 formats simultaneously from single analysis:
- **Email HTML** - Beautiful template with styling
- **PDF** - Print-ready with metrics
- **PowerPoint** - 8-slide branded presentation
- **Podcast** - MP3 audio narration (NotebookLM style)
- **Transcript** - Full text version
- **Summary** - Quick reference (1-2 pages)

### ✅ Human-in-the-Loop Review

Optional manual approval workflow:
- Review pending papers before sending
- Approve/reject with notes
- Archive final decisions
- Metrics on acceptance rate

### ✅ GitHub Actions Deployment

Run completely free without infrastructure:
- Daily scheduled execution (9 AM UTC)
- Email reports delivered daily
- No server, database, or hosting costs
- Scales automatically

### ✅ Dashboard Management

Web interface for:
- Browse collected papers with semantic search
- Real-time chat with papers (RAG-powered)
- Monitor pipeline status
- Review HITL approval queue
- View statistics and trends

---

## API Reference

See [API_REFERENCE.md](./API_REFERENCE.md) for complete endpoint documentation.

### Key Endpoints

**Papers API:**
- `GET /api/papers` - List papers with filtering
- `POST /api/papers/semantic-search` - Search by meaning
- `POST /api/papers/rag-search` - Advanced RAG search

**Chat API:**
- `WebSocket /ws/chat` - Real-time chat with papers (preferred)
- `POST /api/chat/message` - REST fallback

**Pipeline API:**
- `WebSocket /ws/pipeline` - Real-time progress streaming
- `GET /api/pipeline/status` - Poll current status
- `POST /api/pipeline/start` - Trigger execution
- `POST /api/pipeline/stop` - Stop running pipeline

**HITL API:**
- `GET /api/hitl/pending` - List reviews awaiting approval
- `POST /api/hitl/approve` - Approve paper
- `POST /api/hitl/reject` - Reject paper

---

## Deployment Options

### Option 1: GitHub Actions (Free, Recommended)

```bash
1. Push code to GitHub
2. Add GitHub Secrets (Settings → Secrets and variables → Actions)
3. Workflow runs daily automatically
4. Reports emailed to SMTP address
```

**Pros:** Free, no infrastructure, automatic
**Cons:** Limited to daily runs, no always-on API

### Option 2: Docker (Self-Hosted)

```bash
docker-compose up
# Runs locally with Ollama, PostgreSQL
# Access dashboard at http://localhost:3000
```

**Pros:** Full control, always-on service, local Ollama
**Cons:** Requires server, AWS/etc account

### Option 3: Railway/Fly.io (Paid, ~$5-10/month)

Deploy Docker image to managed platform
- Automatic scaling
- Built-in monitoring
- Always-on dashboard access

---

## Troubleshooting

### Pipeline Failing on GitHub Actions

**Problem:** `Error: ENABLE_OLLAMA initialization timeout`

**Solution:** Already fixed in v2.0 - Ollama is automatically disabled in GitHub Actions via `ENABLE_OLLAMA=false` environment variable.

### Email Not Sending

**Check:**
```bash
1. SMTP credentials correct (test with: telnet smtp.gmail.com 587)
2. Gmail: Account → Security → App passwords (if 2FA enabled)
3. Logs show: "[Mailer] Email sent successfully"
```

### Low Relevance Scores

**Adjust:** Edit `config/config.yaml` → `relevance_threshold` (default: 60)

### Ollama Not Detected

**Check:**
```bash
# Ollama running?
curl http://localhost:11434/api/tags

# If not: ollama serve gemma3:4b
# Or disable: export ENABLE_OLLAMA=false
```

---

## Configuration

Edit `config/config.yaml`:

```yaml
data_sources:
  arxiv:
    enabled: true
    categories: [cs.CY, cs.AR, cs.LG]  # Computer Vision, Architecture, Learning
    keywords: [on-device, mobile, edge]

  rss_feeds:
    - url: https://...
      category: news

  enabled_services:
    ollama: true          # Set to false for GitHub Actions
    groq: true
    gemini: true

relevance_threshold: 60   # Minimum score (0-100)

hitl_enabled: true        # Require manual approval
```

---

## Development

### Running Tests

```bash
pytest tests/ -v

# Specific test file:
pytest tests/test_comprehensive.py::TestAnalyzer -v

# With coverage:
pytest --cov=src tests/
```

### Code Style

```bash
black src/ tests/      # Format
isort src/ tests/      # Sort imports
flake8 src/ tests/     # Lint
mypy src/              # Type check
```

### Adding New Report Format

1. Create `src/xxx_generator.py`
2. Implement `class XxxReportGenerator` with `def generate(insights) -> bool`
3. Register in `src/multi_format_orchestrator.py`
4. Add to `MultiFormatReportOrchestrator.generate_all()`

Example (minimal):
```python
from typing import List, Dict

class MyReportGenerator:
    def generate(self, insights: List[Dict]) -> bool:
        """Generate custom report format"""
        try:
            # Generate report
            # Save to results/reports/custom_report.ext
            return True
        except Exception as e:
            logger.error(f"Generator failed: {e}")
            return False
```

---

## Performance

### Typical Execution Time

- **Collection:** 2-3 min (scrape sources)
- **Deduplication:** <1 min (check history)
- **Analysis:** 5-10 min (LLM processing)
- **Quality Check:** 2-3 min (council verification)
- **Report Generation:** 1-2 min (all 6 formats)
- **Email:** <1 min (deliver)
- **Total:** ~15-20 min per run

### Optimization Tips

```python
# .env
ENABLE_OLLAMA=false                  # -3 sec (skip Ollama init)
SKIP_HITL=true                       # -5 sec (no review step)
USE_FASTER_MODELS=true               # -20% time (smaller models)
```

---

## Contributing

1. Create feature branch: `git checkout -b feature/xxx`
2. Make changes with tests
3. Run full test suite: `pytest tests/ -v`
4. Commit: `git commit -m "desc"`
5. Submit PR

---

## License

MIT License - See LICENSE file

---

## Support

- **Issues:** [GitHub Issues](https://github.com/pbtsvinaysukhesh/dea-genai-agent/issues)
- **Docs:** This README + [API_REFERENCE.md](./API_REFERENCE.md) + [DEPLOYMENT.md](./DEPLOYMENT.md)
- **Guides:** See `docs/` directory for detailed guides

---

## Roadmap

- [ ] Support for academic paper full-text extraction
- [ ] Claude integration as LLM option
- [ ] Database persistence (PostgreSQL, MongoDB)
- [ ] Web UI authentication
- [ ] Custom document upload
- [ ] Research team collaboration features
- [ ] API rate limiting and usage quotas
- [ ] Advanced ML ranking (learned-to-rank)

---

**Last Updated:** 2026-02-28
**Version:** 2.0.0
**Status:** Production-ready for GitHub Actions
