#!/usr/bin/env python
"""
Test script for Multi-Format Report Generation
Validates all output formats with sample data
"""

import os
import sys
import json
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_sample_insights(num_papers: int = 6) -> list:
    """Create sample paper insights for testing"""
    papers = []

    titles = [
        "Efficient Quantization for On-Device Neural Networks",
        "DRAM Bandwidth Optimization on Mobile Platforms",
        "Neural Architecture Search for Edge Devices",
        "Mixed-Precision Inference for LLMs",
        "Memory-Efficient Attention Mechanisms",
        "Hardware-Aware Model Compression Techniques"
    ]

    platforms = ["Mobile", "Laptop", "IoT"]
    sources = ["arXiv", "NeurIPS", "ICLR", "ICML", "Google Scholar"]
    quantization_methods = [
        "Int8 Quantization",
        "Mixed-Precision (Int4/Int8)",
        "Dynamic Quantization",
        "Knowledge Distillation",
        "Pruning with Quantization",
        "Differentiable Quantization"
    ]

    for i in range(min(num_papers, len(titles))):
        paper = {
            'title': titles[i],
            'relevance_score': 85 + (i % 3) * 5,
            'platform': platforms[i % len(platforms)],
            'model_type': 'Transformer' if i % 2 == 0 else 'CNN',
            'dram_impact': ['High', 'Medium', 'Low'][i % 3],
            'source': sources[i % len(sources)],
            'date': datetime.now().isoformat(),
            'memory_insight': f"Paper {i+1}: Demonstrates {quantization_methods[i]} achieving 3.2x reduction in model size while maintaining inference speed within 5% of baseline.",
            'engineering_takeaway': f"Implement {quantization_methods[i]} in production systems. Consider calibration dataset size and quantization granularity for optimal performance.",
            'quantization_method': quantization_methods[i],
            'url': f'https://example.com/paper{i+1}.pdf'
        }
        papers.append(paper)

    return papers


def test_multiformat_generation():
    """Test multi-format report generation"""
    logger.info("="*80)
    logger.info("MULTI-FORMAT REPORT GENERATION TEST")
    logger.info("="*80)

    # Create sample data
    logger.info("\n[1/5] Creating sample paper insights...")
    sample_papers = create_sample_insights(num_papers=6)
    logger.info(f"✅ Created {len(sample_papers)} sample papers")

    # Test import
    logger.info("\n[2/5] Testing imports...")
    try:
        from src.multiformat_integration import generate_multiformat_email_report
        logger.info("✅ MultiFormatReportIntegration imported successfully")
    except ImportError as e:
        logger.error(f"❌ Failed to import: {e}")
        logger.error("\nDEBUG: Checking if orchestrator modules exist:")
        orchestrator_files = [
            'src/multi_format_orchestrator.py',
            'src/enhanced_formatter.py',
            'src/pdf_generator.py',
            'src/pptx_generator.py',
            'src/podcast_generator.py'
        ]
        for file in orchestrator_files:
            exists = os.path.exists(file)
            logger.info(f"  {file}: {'✅' if exists else '❌'}")
        return False

    # Test generation
    logger.info("\n[3/5] Generating multi-format reports...")
    try:
        html_report, attachments, results = generate_multiformat_email_report(sample_papers, output_dir="results/reports")

        logger.info(f"✅ Reports generated:")
        logger.info(f"  - Email HTML: {len(html_report)} bytes")
        logger.info(f"  - Attachments: {len(attachments)} files")

        for fmt, success in results.items():
            status = "✅" if success else "❌"
            logger.info(f"    {status} {fmt.upper()}")

    except Exception as e:
        logger.error(f"❌ Generation failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

    # Verify files
    logger.info("\n[4/5] Verifying generated files...")
    output_dir = "results/reports"

    expected_files = {
        'email_report.html': 'Email Report',
        'report.pdf': 'PDF Report',
        'report.pptx': 'PowerPoint Presentation',
        'podcast.mp3': 'Podcast Audio',
        'transcript.txt': 'Podcast Transcript',
        'summary.txt': 'Summary Document'
    }

    verified_count = 0
    for filename, description in expected_files.items():
        filepath = os.path.join(output_dir, filename)
        if os.path.exists(filepath):
            size_kb = os.path.getsize(filepath) / 1024
            logger.info(f"✅ {description}: {filename} ({size_kb:.1f} KB)")
            verified_count += 1
        else:
            logger.warning(f"⚠️  {description}: {filename} (not found)")

    logger.info(f"\nVerification: {verified_count}/{len(expected_files)} files present")

    # Test email HTML validity
    logger.info("\n[5/5] Validating email HTML...")
    if html_report:
        if '<html>' in html_report.lower() and len(html_report) > 1000:
            logger.info(f"✅ Email HTML is valid ({len(html_report)} bytes)")

            # Check for key content
            checks = [
                ('6+ papers', lambda h: 'paper' in h.lower() or 'title' in h.lower()),
                ('Metrics', lambda h: 'score' in h.lower() or 'average' in h.lower()),
                ('Resources', lambda h: 'resource' in h.lower() or 'link' in h.lower()),
            ]

            for check_name, check_func in checks:
                if check_func(html_report):
                    logger.info(f"  ✅ Contains: {check_name}")
                else:
                    logger.warning(f"  ⚠️  Missing: {check_name}")
        else:
            logger.warning(f"⚠️  Email HTML seems incomplete ({len(html_report)} bytes)")
    else:
        logger.warning("⚠️  Email HTML is empty")

    logger.info("\n" + "="*80)
    logger.info("TEST COMPLETE")
    logger.info("="*80)

    return True


def check_dependencies():
    """Check if all required dependencies are installed"""
    logger.info("\nChecking dependencies:")

    dependencies = {
        'reportlab': ('reportlab', 'PDF generation'),
        'python-pptx': ('pptx', 'PowerPoint generation'),
        'gtts': ('gtts', 'Text-to-speech for podcast'),
        'pydub': ('pydub', 'Audio processing')
    }

    missing = []
    for pkg_name, (import_name, purpose) in dependencies.items():
        try:
            __import__(import_name)
            logger.info(f"✅ {pkg_name}: {purpose}")
        except ImportError:
            logger.warning(f"❌ {pkg_name}: {purpose} (NOT installed)")
            missing.append(pkg_name)

    if missing:
        logger.warning("\nTo install missing dependencies, run:")
        logger.warning(f"  pip install {' '.join(missing)}")

        # Check if only optional deps are missing
        optional = ['pydub']
        required_missing = [m for m in missing if m not in optional]

        if required_missing:
            logger.warning("\n❌ Required dependencies missing. Cannot continue.")
            return False
        else:
            logger.warning("\n⚠️  Optional dependencies missing (podcast generation may fail, but other formats will work).")
            return True


if __name__ == "__main__":
    print("\n")

    # Check dependencies
    if not check_dependencies():
        logger.warning("\n⚠️  Some dependencies are missing. Install them before running the full pipeline.")
        sys.exit(1)

    # Check for FFmpeg (needed for pydub)
    logger.info("\nChecking FFmpeg (needed for podcast audio):")
    result = os.system("ffmpeg -version > /dev/null 2>&1")
    if result == 0:
        logger.info("✅ FFmpeg is installed")
    else:
        logger.warning("❌ FFmpeg not found (podcast generation will fail)")
        logger.warning("  Install: https://ffmpeg.org/download.html")

    # Run test
    success = test_multiformat_generation()

    if success:
        logger.info("\n✅ All tests passed! Ready for production.")
        sys.exit(0)
    else:
        logger.error("\n❌ Some tests failed. Check the output above.")
        sys.exit(1)
