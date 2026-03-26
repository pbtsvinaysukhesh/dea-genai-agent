"""
Shared report bundle models for research output generation.

These helpers normalize fetched sources and shortlisted insights into one
payload so email, PDF, PPTX, and podcast generation stay consistent.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


def _first_non_empty(*values: Any, default: str = "") -> str:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return default


def _coerce_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def build_content_excerpt(item: Dict[str, Any], limit: int = 280) -> str:
    text = _first_non_empty(
        item.get("full_text"),
        item.get("abstract"),
        item.get("summary"),
        item.get("content"),
    )
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def normalize_url(url: str) -> str:
    if not url:
        return ""
    url = str(url).strip()
    if not url:
        return ""
    if url.startswith(("http://", "https://", "ftp://")):
        return url
    return "https://" + url


@dataclass
class ResearchSource:
    title: str
    url: str
    source_platform: str
    source_type: str = "unknown"
    published_at: str = ""
    fetched_at: str = ""
    author: str = ""
    tags: List[str] = field(default_factory=list)
    crawl_confidence: float = 0.0
    content_excerpt: str = ""
    has_full_text: bool = False
    content_length: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RankedInsight:
    rank: int
    title: str
    url: str
    source_platform: str
    relevance_score: float
    summary: str = ""
    memory_insight: str = ""
    engineering_takeaway: str = ""
    platform: str = "Unknown"
    model_type: str = "Unknown"
    dram_impact: str = "Unknown"
    score_breakdown: Dict[str, Any] = field(default_factory=dict)
    source_ref: Optional[ResearchSource] = None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        if self.source_ref:
            data["source_ref"] = self.source_ref.to_dict()
        return data


@dataclass
class ReportBundle:
    generated_at: str
    selected_insights: List[RankedInsight]
    source_appendix: List[ResearchSource]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "selected_insights": [item.to_dict() for item in self.selected_insights],
            "source_appendix": [item.to_dict() for item in self.source_appendix],
            "metadata": self.metadata,
        }


def build_research_source(item: Dict[str, Any]) -> Optional[ResearchSource]:
    url = normalize_url(
        _first_non_empty(item.get("url"), item.get("link"), item.get("pdf_url"))
    )
    if not url:
        return None

    excerpt = build_content_excerpt(item)
    title = _first_non_empty(item.get("title"), default="Untitled Source")
    source_platform = _first_non_empty(
        item.get("source"),
        item.get("source_platform"),
        item.get("source_type"),
        default="Unknown",
    )
    source_type = _first_non_empty(item.get("source_type"), default="unknown")
    published_at = _first_non_empty(item.get("published"), item.get("date"))
    fetched_at = _first_non_empty(
        item.get("scraped_at"),
        item.get("collected_at"),
        datetime.utcnow().isoformat() + "Z",
    )
    author = _first_non_empty(item.get("authors"), item.get("author"))
    tags = _coerce_list(item.get("tags"))

    confidence = item.get("crawl_confidence", item.get("hitl_confidence", 0.0))
    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        confidence = 0.0

    return ResearchSource(
        title=title,
        url=url,
        source_platform=source_platform,
        source_type=source_type,
        published_at=published_at,
        fetched_at=fetched_at,
        author=author,
        tags=tags,
        crawl_confidence=confidence,
        content_excerpt=excerpt,
        has_full_text=bool(item.get("has_full_text")),
        content_length=len(_first_non_empty(item.get("full_text"), item.get("summary"))),
        metadata={
            "pdf_url": _first_non_empty(item.get("pdf_url")),
            "original_summary": _first_non_empty(item.get("summary")),
        },
    )


def build_report_bundle(
    insights: List[Dict[str, Any]],
    all_sources: Optional[List[Dict[str, Any]]] = None,
    top_k: int = 6,
) -> ReportBundle:
    all_sources = all_sources or insights

    appendix: List[ResearchSource] = []
    source_map: Dict[str, ResearchSource] = {}
    for item in all_sources:
        source = build_research_source(item)
        if not source:
            continue
        if source.url in source_map:
            continue
        source_map[source.url] = source
        appendix.append(source)

    ranked: List[RankedInsight] = []
    sorted_insights = sorted(
        insights,
        key=lambda x: float(x.get("relevance_score", 0)),
        reverse=True,
    )
    for idx, item in enumerate(sorted_insights[:top_k], 1):
        url = normalize_url(_first_non_empty(item.get("link"), item.get("url")))
        source_ref = source_map.get(url)
        ranked.append(
            RankedInsight(
                rank=idx,
                title=_first_non_empty(item.get("title"), default="Untitled Insight"),
                url=url,
                source_platform=_first_non_empty(
                    item.get("source"),
                    item.get("source_platform"),
                    default="Unknown",
                ),
                relevance_score=float(item.get("relevance_score", 0)),
                summary=_first_non_empty(item.get("summary")),
                memory_insight=_first_non_empty(item.get("memory_insight")),
                engineering_takeaway=_first_non_empty(item.get("engineering_takeaway")),
                platform=_first_non_empty(item.get("platform"), default="Unknown"),
                model_type=_first_non_empty(item.get("model_type"), default="Unknown"),
                dram_impact=_first_non_empty(item.get("dram_impact"), default="Unknown"),
                score_breakdown={
                    "hitl_confidence": item.get("hitl_confidence"),
                    "hitl_status": item.get("hitl_status"),
                    "council_metadata": item.get("council_metadata"),
                },
                source_ref=source_ref,
            )
        )

    return ReportBundle(
        generated_at=datetime.utcnow().isoformat() + "Z",
        selected_insights=ranked,
        source_appendix=appendix,
        metadata={
            "total_selected": len(ranked),
            "total_sources": len(appendix),
        },
    )
