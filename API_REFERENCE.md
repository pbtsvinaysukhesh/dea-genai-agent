# API Reference - Dashboard Backend

Complete documentation of all FastAPI endpoints for the On-Device AI Research Dashboard.

---

## Base URL

```
http://localhost:8000
```

**API Docs:** `http://localhost:8000/docs` (Swagger UI)

---

## Authentication

Currently no authentication required (CORS allows all origins in development).

For production, add:
- Bearer token authentication
- API key validation
- Rate limiting

---

## Papers API

### List All Papers

**Endpoint:** `GET /api/papers`

**Description:** List papers with filtering and pagination

**Query Parameters:**
| Parameter | Type | Default | Range/Notes |
|-----------|------|---------|------------|
| `limit` | integer | 100 | 1-1000 results per page |
| `offset` | integer | 0 | For pagination |
| `platform` | string | - | Filter: "Mobile", "Laptop", "Edge", etc |
| `min_score` | integer | 0 | Relevance score threshold (0-100) |
| `search` | string | - | Keyword search in title/summary |

**Example Request:**
```bash
GET /api/papers?limit=50&offset=0&min_score=70&platform=Mobile
```

**Response (200 OK):**
```json
{
  "papers": [
    {
      "id": "arxiv_2024_001",
      "title": "Efficient On-Device Transformers",
      "source": "arXiv",
      "platform": "Mobile",
      "relevance_score": 95,
      "model_type": "Transformer",
      "dram_impact": "High",
      "memory_insight": "Achieves 40% memory reduction through quantization",
      "engineering_takeaway": "Use 8-bit quantization for mobile deployment",
      "link": "https://arxiv.org/abs/2024.xxxxx",
      "created_at": "2024-02-28T10:30:00Z"
    }
  ],
  "total": 243,
  "limit": 50,
  "offset": 0
}
```

---

### Get Paper by ID

**Endpoint:** `GET /api/papers/{paper_id}`

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `paper_id` | string | Paper unique identifier |

**Example Request:**
```bash
GET /api/papers/arxiv_2024_001
```

**Response (200 OK):**
```json
{
  "id": "arxiv_2024_001",
  "title": "Efficient On-Device Transformers",
  "source": "arXiv",
  "full_text": "Lorem ipsum...",
  "platform": "Mobile",
  "relevance_score": 95,
  ...
}
```

**Response (404 Not Found):**
```json
{
  "detail": "Paper not found"
}
```

---

### Update Paper

**Endpoint:** `PUT /api/papers/{paper_id}`

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `paper_id` | string | Paper unique identifier |

**Request Body:**
```json
{
  "title": "Updated Title",
  "platform": "Mobile",
  "relevance_score": 85
}
```

**Response (200 OK):**
```json
{
  "id": "arxiv_2024_001",
  "title": "Updated Title",
  "updated_at": "2024-02-28T11:30:00Z"
}
```

---

### Delete Paper

**Endpoint:** `DELETE /api/papers/{paper_id}`

**Response (200 OK):**
```json
{
  "message": "Paper deleted",
  "deleted_id": "arxiv_2024_001"
}
```

---

### Semantic Search

**Endpoint:** `POST /api/papers/semantic-search`

**Description:** Search papers using vector similarity (semantic meaning)

**Request Body:**
```json
{
  "query": "What are techniques for reducing memory usage in mobile AI?",
  "top_k": 5,
  "platform": "Mobile",
  "min_score": 70
}
```

**Response (200 OK):**
```json
{
  "query": "What are techniques for reducing memory usage in mobile AI?",
  "results": [
    {
      "id": "arxiv_2024_001",
      "title": "Efficient On-Device Transformers",
      "similarity_score": 0.92,
      "relevance_score": 95,
      "platform": "Mobile"
    }
  ],
  "total": 3,
  "search_time_ms": 145
}
```

---

### RAG Search (Advanced)

**Endpoint:** `POST /api/papers/rag-search`

**Description:** Advanced search combining BM25 (keyword), semantic search, and MMR ranking

**Request Body:**
```json
{
  "query": "on-device quantization techniques",
  "top_k": 5,
  "use_mmr": true,
  "mmr_diversity": 0.5,
  "hybrid": true,
  "bm25_weight": 0.3,
  "semantic_weight": 0.7
}
```

**Response (200 OK):**
```json
{
  "query": "on-device quantization techniques",
  "search_type": "hybrid_mmr",
  "results": [
    {
      "id": "arxiv_2024_005",
      "title": "Integer-only Quantization for Mobile",
      "bm25_score": 8.5,
      "semantic_score": 0.88,
      "mmr_score": 0.85,
      "final_rank": 1
    }
  ],
  "total": 12,
  "search_time_ms": 342
}
```

---

### Similar Papers

**Endpoint:** `GET /api/papers/{paper_id}/similar`

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `paper_id` | string | Reference paper ID |

**Query Parameters:**
| Parameter | Type | Default |
|-----------|------|---------|
| `top_k` | integer | 5 |

**Example Request:**
```bash
GET /api/papers/arxiv_2024_001/similar?top_k=10
```

**Response (200 OK):**
```json
{
  "reference_paper": "Efficient On-Device Transformers",
  "similar_papers": [
    {
      "id": "arxiv_2024_002",
      "title": "MobileNet V4: Architecture Improvements",
      "similarity_score": 0.89
    }
  ],
  "total": 8
}
```

---

## Chat API

### WebSocket Chat (Preferred)

**Endpoint:** `WebSocket /ws/chat`

**Description:** Real-time streaming chat with RAG-powered context retrieval

**Connection:**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/chat');
```

**Message Format (Client → Server):**
```json
{
  "content": "What are the latest advances in on-device AI?",
  "paper_id": "arxiv_2024_001",
  "context": []
}
```

**Response Stream (Server → Client):**
```json
{"type": "token", "content": "The"}
{"type": "token", "content": " latest"}
{"type": "token", "content": " advances"}
...
{"type": "done"}
```

**Error Response:**
```json
{
  "type": "error",
  "message": "Chat service unavailable"
}
```

### REST Chat Fallback

**Endpoint:** `POST /api/chat/message`

**Description:** REST fallback when WebSocket unavailable (slower)

**Request Body:**
```json
{
  "content": "Explain model quantization",
  "paper_id": "arxiv_2024_001",
  "context": []
}
```

**Response (200 OK):**
```json
{
  "response": "Model quantization is a technique...",
  "tokens": 142,
  "ms": 3420
}
```

---

## Pipeline API

### Get Pipeline Status

**Endpoint:** `GET /api/pipeline/status`

**Description:** Get current pipeline execution status (for polling)

**Response (200 OK):**
```json
{
  "status": "running",
  "progress": 45,
  "stage": "analyzing",
  "message": "Analyzing 42 papers with AI",
  "stats": {
    "collected": 42,
    "deduplicated": 38,
    "analyzed": 22,
    "approved": 20
  },
  "started_at": "2024-02-28T09:00:00Z",
  "completed_at": null,
  "error": null
}
```

**Status Values:**
- `idle` - Not running
- `running` - Actively executing
- `completed` - Finished successfully
- `failed` - Execution failed

---

### Start Pipeline

**Endpoint:** `POST /api/pipeline/start`

**Description:** Trigger pipeline execution (non-blocking)

**Request Body:** (empty)
```json
{}
```

**Response (200 OK):**
```json
{
  "status": "started",
  "message": "Pipeline started successfully",
  "progress": 0
}
```

**Response (400 Bad Request):**
```json
{
  "status": "already_running",
  "message": "Pipeline already running",
  "progress": 45
}
```

---

### Stop Pipeline

**Endpoint:** `POST /api/pipeline/stop`

**Description:** Gracefully stop running pipeline

**Response (200 OK):**
```json
{
  "status": "stopped",
  "message": "Pipeline stopped successfully"
}
```

**Response (400 Bad Request):**
```json
{
  "status": "not_running",
  "message": "Pipeline is not running"
}
```

---

### WebSocket Pipeline Progress

**Endpoint:** `WebSocket /ws/pipeline`

**Description:** Real-time pipeline progress streaming

**Connection:**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/pipeline');
ws.send('start');  // Signal to start
```

**Progress Stream (Server → Client):**
```json
{"type": "progress", "progress": 5, "stage": "collection", "message": "📂 Loading config..."}
{"type": "progress", "progress": 15, "stage": "collection", "message": "Collected 42 articles"}
{"type": "progress", "progress": 35, "stage": "analysis", "message": "Analyzing with AI..."}
{"type": "progress", "progress": 75, "stage": "reporting", "message": "Generating reports..."}
{"type": "complete", "progress": 100, "message": "Pipeline complete!", "stats": {...}}
```

---

## HITL API - Human-in-the-Loop Review

### List Pending Reviews

**Endpoint:** `GET /api/hitl/pending`

**Description:** Get papers awaiting human approval

**Response (200 OK):**
```json
{
  "pending": [
    {
      "review_id": "review_001",
      "paper_id": "arxiv_2024_001",
      "title": "Efficient On-Device Transformers",
      "relevance_score": 85,
      "ai_recommendation": "approve",
      "created_at": "2024-02-28T10:30:00Z"
    }
  ],
  "total": 5
}
```

---

### List Approved Reviews

**Endpoint:** `GET /api/hitl/approved`

**Response (200 OK):**
```json
{
  "approved": [
    {
      "review_id": "review_001",
      "paper_id": "arxiv_2024_001",
      "title": "Efficient On-Device Transformers",
      "approved_at": "2024-02-28T11:00:00Z",
      "approved_by": "admin",
      "notes": "Excellent paper on quantization"
    }
  ],
  "total": 42
}
```

---

### List Rejected Reviews

**Endpoint:** `GET /api/hitl/rejected`

**Response (200 OK):**
```json
{
  "rejected": [
    {
      "review_id": "review_002",
      "paper_id": "arxiv_2024_002",
      "title": "Unrelated Paper",
      "rejected_at": "2024-02-28T11:05:00Z",
      "rejected_by": "admin",
      "notes": "Not about on-device AI"
    }
  ],
  "total": 3
}
```

---

### Approve Paper

**Endpoint:** `POST /api/hitl/approve`

**Request Body:**
```json
{
  "review_id": "review_001",
  "notes": "Useful insights on optimization"
}
```

**Response (200 OK):**
```json
{
  "status": "approved",
  "review_id": "review_001",
  "approved_at": "2024-02-28T11:30:00Z"
}
```

---

### Reject Paper

**Endpoint:** `POST /api/hitl/reject`

**Request Body:**
```json
{
  "review_id": "review_002",
  "notes": "Out of scope for this project"
}
```

**Response (200 OK):**
```json
{
  "status": "rejected",
  "review_id": "review_002",
  "rejected_at": "2024-02-28T11:32:00Z"
}
```

---

## Statistics API

### Get Dashboard Statistics

**Endpoint:** `GET /api/stats`

**Description:** Aggregate statistics for dashboard

**Response (200 OK):**
```json
{
  "total_papers": 243,
  "average_relevance": 78.5,
  "highest_score": 99,
  "platforms": {
    "Mobile": 145,
    "Laptop": 65,
    "Edge": 33
  },
  "impacts": {
    "High": 85,
    "Medium": 102,
    "Low": 56
  },
  "model_types": {
    "Transformer": 120,
    "Convolutional": 65,
    "Hybrid": 58
  },
  "sources": {
    "arXiv": 180,
    "GitHub": 43,
    "RSS": 20
  }
}
```

---

## System Health

### Health Check

**Endpoint:** `GET /health`

**Description:** Overall system health

**Response (200 OK):**
```json
{
  "status": "ok",
  "timestamp": "2024-02-28T12:00:00Z",
  "version": "2.0.0"
}
```

### Papers Service Health

**Endpoint:** `GET /api/papers/health`

**Response (200 OK):**
```json
{
  "service": "PapersAPI",
  "rag_available": true,
  "data_service": "ok",
  "embeddings": true
}
```

### Pipeline Service Health

**Endpoint:** `GET /api/pipeline/health`

**Response (200 OK):**
```json
{
  "status": "healthy",
  "timestamp": "2024-02-28T12:00:00Z",
  "service": "pipeline"
}
```

---

## Error Responses

All errors follow this format:

```json
{
  "detail": "Error description",
  "status_code": 400,
  "error_type": "ValueError"
}
```

### Common Status Codes

| Code | Meaning | Example |
|------|---------|---------|
| 200 | Success | Request completed |
| 400 | Bad Request | Invalid parameters |
| 404 | Not Found | Paper ID doesn't exist |
| 500 | Server Error | LLM service down |
| 503 | Service Unavailable | RAG temporarily offline |

---

## Rate Limiting

Currently disabled. For production, implement:

```
1000 requests/minute per IP
100 requests/minute per user (authenticated)
```

---

## WebSocket Message Format

### Standard Message
```json
{
  "type": "token|progress|error|done",
  "content": "text content",
  "timestamp": "2024-02-28T12:00:00Z"
}
```

### Error Message
```json
{
  "type": "error",
  "message": "Service unavailable",
  "code": "SERVICE_DOWN"
}
```

---

## Integration Examples

### Using fetch() in JavaScript

```javascript
// List papers
const response = await fetch('/api/papers?limit=10');
const data = await response.json();
console.log(data.papers);

// Search papers
const search = await fetch('/api/papers/semantic-search', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    query: "quantization",
    top_k: 5
  })
});
```

### Using Python requests

```python
import requests

# Get papers
response = requests.get('http://localhost:8000/api/papers?limit=10')
papers = response.json()['papers']

# RAG search
result = requests.post(
    'http://localhost:8000/api/papers/rag-search',
    json={
        'query': 'mobile optimization',
        'top_k': 5,
        'use_mmr': True
    }
)
papers = result.json()['results']
```

### Using async/await with WebSocket

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/chat');

ws.onopen = () => {
  ws.send(JSON.stringify({
    content: "Explain quantization",
    context: []
  }));
};

ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  if (msg.type === 'token') {
    document.getElementById('output').innerHTML += msg.content;
  } else if (msg.type === 'done') {
    console.log('Chat complete');
  }
};
```

---

**Last Updated:** 2026-02-28
**API Version:** 2.0.0
**Status:** Production
