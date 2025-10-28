#!/usr/bin/env python3
"""
Pre-download models during build phase to avoid runtime delays.
This script is run during the Render build process to cache models before deployment.
"""

import os
import sys

# Set cache directories to /tmp (writable on Render)
os.environ['TRANSFORMERS_CACHE'] = '/tmp/transformers_cache'
os.environ['SENTENCE_TRANSFORMERS_HOME'] = '/tmp/sentence_transformers'
os.environ['HF_HOME'] = '/tmp/huggingface'

print("="*70)
print("MODEL PRE-DOWNLOAD SCRIPT")
print("="*70)
print(f"TRANSFORMERS_CACHE: {os.environ.get('TRANSFORMERS_CACHE')}")
print(f"SENTENCE_TRANSFORMERS_HOME: {os.environ.get('SENTENCE_TRANSFORMERS_HOME')}")
print(f"HF_HOME: {os.environ.get('HF_HOME')}")
print("="*70)

try:
    print("\n[1/1] Downloading SentenceTransformer model: all-MiniLM-L6-v2")
    print("This may take 1-2 minutes...")

    from sentence_transformers import SentenceTransformer

    # Download and cache the model
    model = SentenceTransformer("all-MiniLM-L6-v2")

    print("✓ Model downloaded and cached successfully!")

    # Test the model to ensure it works
    print("\n[Testing] Encoding a test sentence...")
    test_embedding = model.encode("This is a test sentence.")
    print(f"✓ Model test successful! Embedding shape: {test_embedding.shape}")

    print("\n" + "="*70)
    print("MODEL PRE-DOWNLOAD COMPLETE")
    print("="*70)
    sys.exit(0)

except Exception as e:
    print(f"\n✗ ERROR: Failed to download model: {e}", file=sys.stderr)
    print("\nThis is a non-critical error. The model will be downloaded at runtime.", file=sys.stderr)
    # Don't fail the build - allow runtime fallback
    sys.exit(0)
