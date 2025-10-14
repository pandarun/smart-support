#!/usr/bin/env python
"""Quick classification test"""
import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.insert(0, '.')

# Load .env file
from dotenv import load_dotenv
load_dotenv()

print("🔍 Testing Classification System...\n")

# Check API key
api_key = os.getenv('SCIBOX_API_KEY')
if not api_key or api_key == 'your_api_key_here':
    print("❌ SCIBOX_API_KEY not configured in .env file")
    print("   Edit .env and set your actual API key")
    sys.exit(1)

print(f"✅ API Key loaded from .env ({len(api_key)} chars)")

# Test classification
try:
    from src.classification.classifier import classify
    
    print("\n🚀 Classifying: 'Как открыть счет?'")
    print("   (This may take 1-2 seconds on first call...)\n")
    
    result = classify("Как открыть счет?")
    
    print("=" * 70)
    print("✅ CLASSIFICATION SUCCESS")
    print("=" * 70)
    print(f"Inquiry: {result.inquiry}")
    print(f"Category: {result.category}")
    print(f"Subcategory: {result.subcategory}")
    print(f"Confidence: {result.confidence:.2f}")
    print(f"Processing Time: {result.processing_time_ms}ms")
    print("=" * 70)
    print("\n✅ System is working correctly!")
    
except Exception as e:
    print(f"\n❌ Classification failed: {e}")
    import traceback
    traceback.print_exc()
    print("\nTroubleshooting:")
    print("1. Check API key is valid at https://llm.t1v.scibox.tech/")
    print("2. Check internet connectivity: ping llm.t1v.scibox.tech")
    print("3. Try increasing timeout: Add API_TIMEOUT=5.0 to .env")
    sys.exit(1)
