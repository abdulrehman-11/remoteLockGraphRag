#!/usr/bin/env python3
"""
Pre-download models during build phase to avoid runtime delays.
This script is run during the Render build process to cache models before deployment.

NOTE: As of the memory optimization update, we now use Gemini API for embeddings
instead of local SentenceTransformer models. This reduces memory usage by ~300MB
which is critical for the Render free tier (512MB limit).

No model download is needed - keeping this file for future use if needed.
"""

import os
import sys

print("="*70)
print("MODEL PRE-DOWNLOAD SCRIPT")
print("="*70)
print("Using Gemini API for embeddings - no local model download needed")
print("This saves ~300MB of memory (PyTorch + SentenceTransformer)")
print("="*70)

# No model download needed - using API-based embeddings
print("\n✓ Build preparation complete")
print("✓ Embeddings will be generated via Gemini API at runtime")
print("✓ Zero local memory footprint for embeddings\n")

print("="*70)
print("BUILD SCRIPT COMPLETE")
print("="*70)
sys.exit(0)

# LEGACY CODE (commented out - no longer needed with API-based embeddings)
#
# SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# CACHE_DIR = os.path.join(SCRIPT_DIR, 'model_cache')
# os.makedirs(CACHE_DIR, exist_ok=True)
# os.makedirs(os.path.join(CACHE_DIR, 'transformers'), exist_ok=True)
# os.makedirs(os.path.join(CACHE_DIR, 'sentence_transformers'), exist_ok=True)
# os.makedirs(os.path.join(CACHE_DIR, 'huggingface'), exist_ok=True)
#
# os.environ['TRANSFORMERS_CACHE'] = os.path.join(CACHE_DIR, 'transformers')
# os.environ['SENTENCE_TRANSFORMERS_HOME'] = os.path.join(CACHE_DIR, 'sentence_transformers')
# os.environ['HF_HOME'] = CACHE_DIR
#
# try:
#     print("\n[1/1] Downloading SentenceTransformer model: all-MiniLM-L6-v2")
#     print("This may take 1-2 minutes...")
#     from sentence_transformers import SentenceTransformer
#     model = SentenceTransformer("all-MiniLM-L6-v2")
#     print("✓ Model downloaded and cached successfully!")
#     test_embedding = model.encode("This is a test sentence.")
#     print(f"✓ Model test successful! Embedding shape: {test_embedding.shape}")
#     sys.exit(0)
# except Exception as e:
#     print(f"\n✗ ERROR: Failed to download model: {e}", file=sys.stderr)
#     print("\nThis is a non-critical error. The model will be downloaded at runtime.", file=sys.stderr)
#     sys.exit(0)
