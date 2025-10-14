"""
CLI interface for Template Retrieval Module.

Provides command-line access to template retrieval functionality:
- Single query retrieval with classification results
- Validation testing against ground truth datasets
- Formatted output with similarity scores and confidence levels

Usage:
    # Single retrieval
    python -m src.cli.retrieve "Как открыть накопительный счет?" \\
        --category "Счета и вклады" \\
        --subcategory "Открытие счета"

    # Validation run
    python -m src.cli.retrieve --validate \\
        data/validation/retrieval_validation_dataset.json
"""

import os
import sys
import argparse
import asyncio
from typing import Optional

from src.retrieval.embeddings import EmbeddingsClient, precompute_embeddings
from src.retrieval.retriever import TemplateRetriever
from src.retrieval.models import RetrievalRequest


def format_retrieval_results(response) -> str:
    """
    Format retrieval response for console display.

    Args:
        response: RetrievalResponse object

    Returns:
        Formatted string with results
    """
    output = []
    output.append("\n" + "=" * 80)
    output.append("RETRIEVAL RESULTS")
    output.append("=" * 80)
    output.append(f"\nQuery: {response.query}")
    output.append(f"Category: {response.category} > {response.subcategory}")
    output.append(f"Processing time: {response.processing_time_ms:.1f}ms")
    output.append(f"Total candidates: {response.total_candidates}")

    # Display warnings if any
    if response.warnings:
        output.append(f"\n⚠️  Warnings:")
        for warning in response.warnings:
            output.append(f"   - {warning}")

    # Display results
    if not response.results:
        output.append("\n❌ No templates found")
    else:
        output.append(f"\n📋 Top {len(response.results)} Templates:")
        output.append("")

        for result in response.results:
            # Confidence emoji
            confidence_emoji = {
                "high": "🟢",
                "medium": "🟡",
                "low": "🔴"
            }.get(result.confidence_level, "⚪")

            output.append(f"#{result.rank} {confidence_emoji} Score: {result.similarity_score:.3f} ({result.confidence_level} confidence)")
            output.append(f"   Q: {result.template_question}")

            # Truncate answer for display
            answer_preview = result.template_answer[:150]
            if len(result.template_answer) > 150:
                answer_preview += "..."
            output.append(f"   A: {answer_preview}")
            output.append("")

    output.append("=" * 80 + "\n")

    return "\n".join(output)


async def run_retrieval(
    query: str,
    category: str,
    subcategory: str,
    top_k: int = 5,
    faq_path: Optional[str] = None
) -> None:
    """
    Run single template retrieval.

    Args:
        query: Customer inquiry text
        category: Classified category
        subcategory: Classified subcategory
        top_k: Number of templates to return
        faq_path: Path to FAQ database (defaults to env var)
    """
    print("Initializing Template Retrieval Module...")
    print("⏳ Precomputing embeddings (this may take 30-60 seconds)...\n")

    # Get FAQ path from environment if not provided
    if faq_path is None:
        faq_path = os.getenv("FAQ_PATH", "docs/smart_support_vtb_belarus_faq_final.xlsx")

    # Initialize embeddings client
    embeddings_client = EmbeddingsClient()

    # Precompute embeddings
    try:
        cache = await precompute_embeddings(
            faq_path=faq_path,
            embeddings_client=embeddings_client,
            batch_size=20
        )
    except FileNotFoundError:
        print(f"❌ Error: FAQ database not found at {faq_path}")
        print("   Set FAQ_PATH environment variable or check file location")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error during embedding precomputation: {e}")
        sys.exit(1)

    # Initialize retriever
    retriever = TemplateRetriever(embeddings_client, cache)

    print(f"✅ Ready! Cache contains {cache.stats['total_templates']} templates\n")

    # Create retrieval request
    request = RetrievalRequest(
        query=query,
        category=category,
        subcategory=subcategory,
        top_k=top_k
    )

    # Retrieve templates
    try:
        response = retriever.retrieve(request)
    except Exception as e:
        print(f"❌ Error during retrieval: {e}")
        sys.exit(1)

    # Display results
    print(format_retrieval_results(response))


async def run_validation(dataset_path: str, faq_path: Optional[str] = None) -> None:
    """
    Run validation against ground truth dataset.

    Args:
        dataset_path: Path to validation dataset JSON
        faq_path: Path to FAQ database (defaults to env var)
    """
    print("Initializing Template Retrieval Module for Validation...")
    print("⏳ Precomputing embeddings (this may take 30-60 seconds)...\n")

    # Get FAQ path from environment if not provided
    if faq_path is None:
        faq_path = os.getenv("FAQ_PATH", "docs/smart_support_vtb_belarus_faq_final.xlsx")

    # Initialize embeddings client
    embeddings_client = EmbeddingsClient()

    # Precompute embeddings
    try:
        cache = await precompute_embeddings(
            faq_path=faq_path,
            embeddings_client=embeddings_client,
            batch_size=20
        )
    except FileNotFoundError:
        print(f"❌ Error: FAQ database not found at {faq_path}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error during embedding precomputation: {e}")
        sys.exit(1)

    # Initialize retriever
    retriever = TemplateRetriever(embeddings_client, cache)

    print(f"✅ Ready! Cache contains {cache.stats['total_templates']} templates\n")

    # Import validator modules
    try:
        from src.retrieval.validator import (
            run_validation as run_validation_module,
            save_validation_results,
            format_validation_report
        )
    except ImportError as e:
        print(f"❌ Error: Failed to import validation module: {e}")
        sys.exit(1)

    # Run validation
    print(f"Running validation against {dataset_path}...\n")

    try:
        validation_result = run_validation_module(
            dataset_path=dataset_path,
            retriever=retriever,
            top_k=5
        )
    except FileNotFoundError:
        print(f"❌ Error: Validation dataset not found at {dataset_path}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error during validation: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Display validation report
    report = format_validation_report(validation_result)
    print(report)

    # Save results to file
    import datetime
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    results_path = f"data/results/retrieval_validation_{timestamp}.json"

    try:
        save_validation_results(validation_result, results_path)
        print(f"\n💾 Results saved to: {results_path}\n")
    except Exception as e:
        print(f"\n⚠️  Warning: Failed to save results: {e}\n")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Template Retrieval CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Retrieve templates for a query
  python -m src.cli.retrieve "Как открыть накопительный счет?" \\
      --category "Счета и вклады" \\
      --subcategory "Открытие счета"

  # Run validation
  python -m src.cli.retrieve --validate data/validation/retrieval_validation_dataset.json

Environment Variables:
  SCIBOX_API_KEY    Scibox API key (required)
  FAQ_PATH          Path to FAQ Excel database (default: docs/smart_support_vtb_belarus_faq_final.xlsx)
  EMBEDDING_MODEL   Embedding model (default: bge-m3)
        """
    )

    # Validation mode
    parser.add_argument(
        "--validate",
        type=str,
        metavar="DATASET_PATH",
        help="Run validation against ground truth dataset (JSON file)"
    )

    # Single retrieval mode arguments
    parser.add_argument(
        "query",
        nargs="?",
        help="Customer inquiry text (required for single retrieval)"
    )

    parser.add_argument(
        "--category",
        type=str,
        help="Classified category (required for single retrieval)"
    )

    parser.add_argument(
        "--subcategory",
        type=str,
        help="Classified subcategory (required for single retrieval)"
    )

    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of templates to return (default: 5)"
    )

    parser.add_argument(
        "--faq-path",
        type=str,
        help="Path to FAQ Excel database (overrides FAQ_PATH env var)"
    )

    args = parser.parse_args()

    # Check for validation mode
    if args.validate:
        asyncio.run(run_validation(
            dataset_path=args.validate,
            faq_path=args.faq_path
        ))
    else:
        # Single retrieval mode - require query, category, subcategory
        if not args.query:
            parser.error("query is required for single retrieval (or use --validate for validation mode)")

        if not args.category:
            parser.error("--category is required for single retrieval")

        if not args.subcategory:
            parser.error("--subcategory is required for single retrieval")

        asyncio.run(run_retrieval(
            query=args.query,
            category=args.category,
            subcategory=args.subcategory,
            top_k=args.top_k,
            faq_path=args.faq_path
        ))


if __name__ == "__main__":
    main()
