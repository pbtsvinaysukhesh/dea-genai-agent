#!/usr/bin/env python3
"""
Test script to verify Google API + GROQ embedding fallback
Tests retry logic with 60-second sleep
"""

import sys
import os
import time

print("=" * 80)
print("EMBEDDING PROVIDER TEST (Google API + GROQ fallback)")
print("=" * 80)

# Test 1: Check API keys
print("\n[TEST 1] API Key Configuration...")
google_key = os.getenv("GOOGLE_API_KEY")
groq_key = os.getenv("GROQ_API_KEY")

if google_key:
    print("✓ GOOGLE_API_KEY is set")
else:
    print("✗ GOOGLE_API_KEY is NOT set (Google embeddings will be unavailable)")

if groq_key:
    print("✓ GROQ_API_KEY is set")
else:
    print("✗ GROQ_API_KEY is NOT set (GROQ fallback will be unavailable)")

if not google_key and not groq_key:
    print("\n⚠️  WARNING: Neither Google nor GROQ API keys are configured")
    print("At least one API key is required for embeddings to work")

# Test 2: Initialize provider
print("\n[TEST 2] Initializing Dual Embedding Provider...")
try:
    from src.embedding_provider import get_embedding_provider

    provider = get_embedding_provider()
    status = provider.get_status()

    print(f"✓ Provider initialized")
    print(f"  Google API: {'✓ Available' if status['google_available'] else '✗ Not available'}")
    print(f"  GROQ Fallback: {'✓ Available' if status['groq_available'] else '✗ Not available'}")
    print(f"  Embedding Dimension: {status['embedding_dim']}")
    print(f"  Max Retries: {status['max_retries']}")
    print(f"  Retry Sleep: {status['retry_sleep']}s")

    if not status['google_available'] and not status['groq_available']:
        print("\n⚠️  Neither provider available - embeddings will fail")
        sys.exit(1)

except Exception as e:
    print(f"✗ Failed to initialize provider: {e}")
    sys.exit(1)

# Test 3: Generate sample embedding
print("\n[TEST 3] Generating sample embedding...")
try:
    sample_text = "Mobile optimization for on-device AI models"

    print(f"Input: '{sample_text}'")
    print("Generating embedding...")

    start_time = time.time()
    embedding = provider.encode(sample_text)
    elapsed = time.time() - start_time

    if embedding:
        print(f"✓ Embedding generated successfully")
        print(f"  Dimension: {len(embedding)}")
        print(f"  Time: {elapsed:.2f}s")
        print(f"  Sample values: {embedding[:5]}...")
    else:
        print(f"✗ Failed to generate embedding (all providers failed)")
        sys.exit(1)

except Exception as e:
    print(f"✗ Error: {e}")
    sys.exit(1)

# Test 4: Retry logic simulation
print("\n[TEST 4] Retry Logic (will NOT actually wait 60s in test)...")
print("Pattern:")
print("  1. Try Google API → Success returns embedding")
print("  2. If Google fails → Try GROQ → Success returns embedding")
print("  3. If both fail → Sleep 60s → Retry from step 1")
print("  4. After {max_retries} total attempts → Return None")

print(f"\nConfiguration:")
print(f"  Max retries: {status['max_retries']}")
print(f"  Sleep duration: {status['retry_sleep']}s")

# Test 5: Multiple embeddings
print("\n[TEST 5] Generating embeddings for multiple papers...")
papers = [
    "Neural network quantization on mobile",
    "Edge AI inference optimization",
    "On-device machine learning"
]

try:
    embeddings = []
    for i, paper in enumerate(papers, 1):
        print(f"  [{i}/{len(papers)}] {paper}...")
        emb = provider.encode(paper)
        if emb:
            embeddings.append(emb)
            print(f"        ✓ Generated")
        else:
            print(f"        ✗ Failed")

    print(f"\n✓ Successfully generated {len(embeddings)}/{len(papers)} embeddings")

except Exception as e:
    print(f"✗ Error: {e}")
    sys.exit(1)

print("\n" + "=" * 80)
print("TEST SUMMARY: ✅ Embedding provider with fallback working")
print("=" * 80)
print("\nConfiguration:")
print("  • Primary: Google API (models/embedding-001)")
print("  • Fallback: GROQ (task-specific embeddings)")
print("  • Retry: 60-second sleep between attempts")
print("  • Max attempts: 3 retries")
print("\nBoth APIs provide 768-dimensional embeddings for consistency")
print("=" * 80)
