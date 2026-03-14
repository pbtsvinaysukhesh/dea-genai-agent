# High Level Design - DEA AI Research Agent

## 🎯 **Architecture Overview**

```
┌─────────────────────┐   ┌─────────────────────┐
│   Data Sources      │   │    GitHub Actions   │
│  • arXiv (RSS/API)  │◄──▶│     (Daily 9AM)    │
│  • Google Scholar   │   │                     │
│  • RSS Feeds        │   │  ┌─────────────────┐ │
│  • GitHub Repos     │   │  │   Local Run      │ │
└──────────┬──────────┘   │  └─────────────────┘ │
           │              │                      │
           ▼              │                      │
┌─────────────────────┐   │                      │
│   Preprocessing     │   │                      │
│  • Deduplication    │◄──┘                      │
│  • Vector Filter    │                           │
└──────────┬──────────┘                           │
           │                                       │
           ▼                                       │
┌─────────────────────┐                           │
│   AI Analysis       │                           │
│  • Multi-LLM        │◄──────────────────────────┘
│    Council         │
│  • Groq→Gemini     │
│  • CrewAI (opt)    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Multi-Format       │
│  Generation         │
│ • Email HTML        │
│ • PDF Report        │
│ • PPTX Slides       │
│ • Podcast MP3       │
│ • Transcript        │
│ • Summary JSON      │
└──────────┬──────────┘
           │
           ├─────────► Email (SMTP)
           └─────────► GitHub Artifact (ZIP)
```

## 🧠 **Core Components**

### 1. **Data Pipeline** (`main.py`)
```
1129 raw → 50 filtered → AI analysis → 6+ reports
```

### 2. **Vector Store** (`src/qdrant_vector_store.py`)
```
• Qdrant v1.11 (query_points)
• 768-dim Gemma embeddings
• Duplicate detection (0.95 cosine)
• Persistent: results/vector_db/
```

### 3. **LLM Council** (`src/ai_council.py`)
```
Groq (llama3-70b) → Gemini fallback
Score consensus: 3-LLM voting
Fallback chain prevents failures
```

### 4. **Scraping** (`src/deep_scraper.py`)
```
Playwright → arXiv PDFs → 1K chars/paper
OpenReview → reviews/comments
```

### 5. **RAG Search** (`src/hybrid_search.py`)
```
α=0.6·Semantic + 0.4·BM25 + MMR(λ=0.5)
Top-K=10 diverse results
```

### 6. **Reports** (`src/multi_format_orchestrator.py`)
```
Email → PDF → PPTX → Podcast → Transcript → Summary
Single analysis → 6 formats simultaneously
```

## 🔧 **Data Flow**

```
1. Collector: RSS/arXiv/GitHub → JSON articles
2. Filter: Vector dedup + title match → 50 new
3. Judge: LLM preliminary score → threshold 60
4. Council: 3-LLM analysis → consensus score
5. HITL: Auto-approve 85%+ confidence
6. Archive: JSON + metadata
7. Generate: 6 formats parallel
8. Email: Only unsent papers
```

## 🛡️ **Error Handling**

```
Groq 429 → Gemini
Gemini fail → Hash embeddings
No embeddings → Keyword-only
Scraping fail → Abstract only
Email fail → Local file
```

## 📊 **Storage**

```
results/vector_db/           # Qdrant (1K+ papers)
data/history.json            # Recent analysis
data/email_sent_tracker.json # Email dedup
data/hitl_review/            # Pending approvals
results/reports/             # Generated files
```

## ⚡ **Performance**

```
Collection:     2min
Deduplication:  30s
LLM Analysis:   8min
Report Gen:     2min
Email:          10s
─────────────────────────────────
Total:         12-15min daily ✓
```

## 🔗 **APIs & Dashboard**

```
FastAPI backend + WebSocket
localhost:8000/docs → Swagger
localhost:3000 → Frontend SPA

• /api/papers → Semantic search
• /ws/pipeline → Live progress
• /api/hitl → Manual review
• /api/stats → Pipeline metrics
```

## 🧹 **GitHub Strategy**

```
.gitignore: results/, logs/, data/
CI: GitHub Artifacts (30-day ZIP)
Local: Persistent vector_db/
```

**Scalable, resilient, FREE TIER PRODUCTION!** 🎉

