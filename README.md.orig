<<<<<<< HEAD
# README - DEA  AI Research Intelligence 
=======
# DEA AI Research Intelligence 🚀
>>>>>>> f650ea3 (fix)

[![GitHub Actions Status](https://github.com/pbtsvinaysukhesh/dea-genai-agent/workflows/Tests/badge.svg)](https://github.com/pbtsvinaysukhesh/dea-genai-agent/actions)
[![CodeQL](https://github.com/pbtsvinaysukhesh/dea-genai-agent/workflows/CodeQL/badge.svg)](https://github.com/pbtsvinaysukhesh/dea-genai-agent/actions)

**Daily AI Research Pipeline** that discovers, analyzes, and delivers insights on **on-device AI, memory optimization, and edge computing** research papers.

**100% FREE TIER** - GitHub Actions + local embeddings. **No servers required**.

## 🎯 **What It Does (Daily)**

1. **Collects** 1K+ papers (arXiv, RSS, GitHub, Scholar)
2. **Filters** duplicates (vector store + title matching)
3. **Analyzes** with multi-LLM council (Groq → Gemini fallback)
4. **Generates** 6 formats: **Email + PDF + PPTX + Podcast + Transcript + Summary**
5. **Emails** report (6+ new papers only)
6. **Archives** to GitHub Artifacts (30-day retention)

```
1129 papers → 50 new → AI Council → 6 reports → 📧 Email → 📦 Artifact
```

## 🚀 **1-Minute Setup**

### GitHub Actions (Recommended - Free)
```bash
1. Fork/Star repo
2. Settings → Secrets → Add:
   - `GROQ_API_KEY` (groq.com)
   - `GOOGLE_API_KEY` (ai.google.dev)
   - `SMTP_*` (Gmail/Outlook)
3. Actions → "Scheduled AI Pipeline" → Run
```

### Local Run
```bash
git clone https://github.com/pbtsvinaysukhesh/dea-genai-agent
cd dea-genai-agent
pip install -r requirements.txt
python main.py  # <- Generates everything!
```

## 📊 **Live Results**

**Daily Reports:** [GitHub Artifacts](https://github.com/pbtsvinaysukhesh/dea-genai-agent/actions)
**Vector DB:** `results/vector_db/` (persistent, ~1K papers)

## 🛠 **Technology Stack**

```
LLMs: Groq (free), Gemini (fallback), Ollama (local)
Search: Qdrant + BM25 + MMR
Scraping: Playwright (PDFs)
Reports: ReportLab(PDF), python-pptx(PPT), gTTS(audio)
Backend: FastAPI + WebSocket
Frontend: HTML/JS SPA
CI/CD: GitHub Actions (free)
```

## 🎛️ **Configuration** (`config/config.yaml`)

```yaml
system:
  relevance_threshold: 60  # Only score ≥60
  use_vectors: true        # Qdrant dedup

sources:
  arxiv_queries: [...]     # 15+ specialized queries
  rss_feeds: [...]         # Apple ML, Qualcomm, Meta AI
  github.enabled: true     # Code repos (50+ stars)

email:
  recipients: ["you@email.com"]
```

## 📈 **Performance**

```
Time: 15-20 min daily
Papers: 1K collected → 50 analyzed → 6+ emailed
Formats: Email, PDF, PPTX, Podcast, Transcript, Summary
Cost: $0 (free tier)
```

## 🔍 **Vector Store Query Example**

```python
from src.qdrant_vector_store import VectorStore
vs = VectorStore()
print(vs.get_stats())  # {'total_papers': 1247, 'added': 1247}
similar = vs.find_similar({'title': 'Quantized LLM Mobile'})
```

## 🕷️ **Playwright Scraping**

```
RSS/arXiv → 1K titles
↓
DeepScraper → Playwright
  ↓
arxiv.org → Click PDF → Extract 1K+ chars
openreview.net → Scrape reviews
↓
"Extracted 1356 chars" ✓
```

## 📧 **Email Delivery**

```
Only NEW papers (email tracker prevents duplicates)
Subject: "On-Device AI Research - 6 New Papers"
Attachments: PDF, PPTX, MP3 podcast
```

## 🎯 **Dashboard** (`localhost:3000`)

```
• Semantic paper search
• RAG chat with papers
• Pipeline progress (live)
• HITL approval queue
• Statistics dashboard
```

## 🛠 **Extending**

**New Report Format:**


### ✅ Multi-Format Report Generation

Generate 6 formats simultaneously from single analysis:
- **Email HTML** - Beautiful template with styling
- **PDF** - Print-ready with metrics
- **PowerPoint** - 8-slide branded presentation
- **Podcast** - MP3 audio narration (NotebookLM style)
- **Transcript** - Full text version
- **Summary** - Quick reference (1-2 pages)


```python
class NewReportGenerator:
    def generate(self, insights):
        # Your logic
        return True

# Register in multi_format_orchestrator.py
```

## 🧹 **Cleanup Complete**

**Removed Unused:**
```
✂️  On-device...docx (old spec)
✂️  podcast_*.mp3 (test files)
✂️  transcript.txt (temp)
✂️  summary.txt/json (superseded)
✂️  test_embedding*.py (redundant)
```

**.gitignore:** `results/`, `__pycache__/`, `.venv/`, `*.log`

**README:** Updated (this file) - concise + actionable

## 📋 **Next Steps**

```
1. [✓] pip install -r requirements.txt
2. [✓] python main.py (local test)
3. [✓] Add GitHub Secrets
4. [ ] Actions → Run "Scheduled AI Pipeline"
5. [ ] Check email + Artifacts
```

**PRODUCTION READY!** 🎉

**Questions?** Open issue or comment here.
