#!/usr/bin/env python3
"""
Script to run Template Retrieval Module validation with v2 dataset.

Uses the new validation dataset that matches actual FAQ category structure.
"""

import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables from .env
load_dotenv(project_root / ".env")

from src.retrieval.embeddings import EmbeddingsClient, precompute_embeddings
from src.retrieval.retriever import TemplateRetriever
from src.retrieval.validator import run_validation, save_validation_results, format_validation_report


async def main():
    """Run validation with v2 dataset."""

    # Configuration
    faq_path = "docs/smart_support_vtb_belarus_faq_final.xlsx"
    dataset_path = "data/validation/retrieval_validation_dataset_v2.json"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"data/results/retrieval_validation_v2_{timestamp}.json"

    print("=" * 80)
    print("Template Retrieval Module - Validation with V2 Dataset")
    print("=" * 80)
    print(f"\nFAQ file: {faq_path}")
    print(f"Dataset: {dataset_path}")
    print(f"Output: {output_path}\n")

    # Initialize embeddings client
    api_key = os.getenv("SCIBOX_API_KEY")
    if not api_key:
        print("❌ Error: SCIBOX_API_KEY not found in environment")
        sys.exit(1)

    print("✓ Initializing embeddings client...")
    embeddings_client = EmbeddingsClient(api_key=api_key, model="bge-m3")

    # Precompute embeddings
    print("✓ Precomputing embeddings from FAQ file...")
    cache = await precompute_embeddings(
        faq_path=faq_path,
        embeddings_client=embeddings_client,
        batch_size=10
    )

    print(f"✓ Loaded {len(cache)} templates")
    print(f"✓ Precomputation time: {cache.precompute_time:.2f}s\n")

    # Initialize retriever
    print("✓ Initializing retriever...")
    retriever = TemplateRetriever(embeddings_client, cache)

    # Run validation
    print("✓ Running validation...\n")
    validation_result = run_validation(
        dataset_path=dataset_path,
        retriever=retriever,
        top_k=5
    )

    # Save results
    print(f"\n✓ Saving results to {output_path}...")
    save_validation_results(validation_result, output_path)

    # Print report
    print("\n" + format_validation_report(validation_result))

    # Exit with appropriate code
    if validation_result.passes_quality_gate:
        print("\n✅ Validation PASSED - Top-3 accuracy ≥80%")
        sys.exit(0)
    else:
        print("\n❌ Validation FAILED - Top-3 accuracy <80%")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
