import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _sample_insights():
    return [
        {
            "title": "Cache-Aware On-Device LLM Serving",
            "summary": "Optimizes KV cache scheduling for mobile inference.",
            "executive_summary": "The paper shows how cache-aware scheduling reduces memory stalls on phones.",
            "why_it_matters": "It gives engineers a path to better latency without changing the whole model.",
            "engineering_takeaway": "Profile cache churn before tuning kernels.",
            "implementation_guidance": "Watch for latency regressions when context length spikes.",
            "key_metrics": ["18 percent lower memory traffic", "11 percent lower latency"],
            "relevance_score": 92,
            "platform": "Mobile",
            "model_type": "LLM",
            "quantization_method": "INT4",
            "dram_impact": "High",
            "source": "arXiv",
        },
        {
            "title": "Streaming Activations for Edge Transformers",
            "summary": "Streams activations instead of materializing every intermediate tensor.",
            "executive_summary": "The core idea is trading a bit of scheduling complexity for much lower memory pressure.",
            "why_it_matters": "Teams can reduce peak memory use on constrained devices.",
            "engineering_takeaway": "Treat memory movement as part of the architecture decision.",
            "implementation_guidance": "The catch is that kernel fusion and execution ordering matter more.",
            "key_metrics": ["24 percent lower peak memory"],
            "relevance_score": 88,
            "platform": "Edge",
            "model_type": "Transformer",
            "quantization_method": "Mixed Precision",
            "dram_impact": "High",
            "source": "OpenReview",
        },
        {
            "title": "Quantization Policy for Mobile NPUs",
            "summary": "Compares quantization policies across phone NPUs.",
            "executive_summary": "Not every low-bit setting survives contact with real hardware pipelines.",
            "why_it_matters": "It highlights where paper wins can disappear in deployment.",
            "engineering_takeaway": "Benchmark on-device, not just in desktop emulation.",
            "implementation_guidance": "The main tradeoff is stability versus absolute compression.",
            "key_metrics": ["9 percent accuracy drop avoided"],
            "relevance_score": 84,
            "platform": "Mobile",
            "model_type": "LLM",
            "quantization_method": "INT8",
            "dram_impact": "Medium",
            "source": "Qualcomm",
        },
    ]


def _make_tmp(name: str) -> Path:
    path = ROOT / "results" / "test_tmp" / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_provider_priority_prefers_best_available():
    from src.podcast_generator import PodcastGenerator

    generator = PodcastGenerator(output_dir=str(_make_tmp("providers-edge")))
    generator.has_edge_tts = True
    generator.has_pydub = True
    generator.has_google_tts = True
    generator.google_client = object()
    generator.has_gtts = True

    assert generator._iter_available_providers() == ["edge", "google", "gtts"]


def test_provider_priority_falls_back_cleanly():
    from src.podcast_generator import PodcastGenerator

    generator = PodcastGenerator(output_dir=str(_make_tmp("providers-fallback")))
    generator.has_edge_tts = False
    generator.has_google_tts = True
    generator.google_client = object()
    generator.has_pydub = True
    generator.has_gtts = True

    assert generator._iter_available_providers() == ["google", "gtts"]

    generator.has_google_tts = False
    generator.google_client = None
    assert generator._iter_available_providers() == ["gtts"]


def test_dialog_is_two_speaker_and_conversational():
    from src.podcast_generator import PodcastGenerator

    generator = PodcastGenerator(output_dir=str(_make_tmp("dialog")))
    dialog = generator.build_dialog(_sample_insights())

    assert dialog
    assert {speaker for speaker, _ in dialog} == {"Host", "Analyst"}
    assert dialog[0][0] == "Host"
    assert sum("welcome" in text.lower() for _, text in dialog) == 1
    assert len(dialog) <= generator.podcast_config["max_turns"]
    assert all(len(text.split()) < 80 for _, text in dialog)

    for index in range(1, len(dialog)):
        assert dialog[index][0] != dialog[index - 1][0]


def test_generate_uses_same_dialog_for_transcript():
    from src.podcast_generator import PodcastGenerator

    tmp_path = _make_tmp("transcript")
    generator = PodcastGenerator(output_dir=str(tmp_path), generate_wav=False)
    fixed_dialog = [
        ("Host", "Hello everyone, welcome to the Vinay DEA podcast."),
        ("Analyst", "Today we are focusing on memory movement and deployable wins."),
    ]

    generator.build_dialog = lambda insights: fixed_dialog
    generator._render_dialog = lambda dialog, run_id: (tmp_path / "podcast_test.mp3", "gtts")
    generator._embed_metadata = lambda *args, **kwargs: True

    result = generator.generate(_sample_insights(), episode_number="test")

    transcript_path = result["transcript"]
    assert transcript_path is not None
    transcript = Path(transcript_path).read_text(encoding="utf-8")
    assert "Host:" in transcript
    assert "Analyst:" in transcript
    assert "memory movement and deployable wins" in transcript
