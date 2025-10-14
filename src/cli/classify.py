"""
Classification Module - CLI Interface

Command-line interface for classification operations.
Supports single, batch, and validation modes.

Constitution Compliance:
- Principle II: User-Centric Design (operator-friendly CLI)
- User Story 1: Single inquiry classification
"""

import sys
import argparse
from pathlib import Path

import asyncio
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from src.classification.classifier import classify, classify_batch, ClassificationError
from src.classification.validator import run_validation
from src.utils.logging import setup_logging


def format_result(result) -> str:
    """
    Format classification result for display.
    
    Args:
        result: ClassificationResult object
        
    Returns:
        Formatted string for console output
    """
    output = []
    output.append("\n" + "=" * 70)
    output.append("CLASSIFICATION RESULT")
    output.append("=" * 70)
    output.append(f"Inquiry: {result.inquiry[:100]}...")
    output.append(f"Category: {result.category}")
    output.append(f"Subcategory: {result.subcategory}")
    output.append(f"Confidence: {result.confidence:.2f}")
    output.append(f"Processing Time: {result.processing_time_ms}ms")
    output.append(f"Timestamp: {result.timestamp}")
    output.append("=" * 70)
    
    return "\n".join(output)


def classify_single(inquiry: str, verbose: bool = False) -> int:
    """
    Classify a single inquiry.
    
    Args:
        inquiry: Inquiry text to classify
        verbose: Enable verbose output
        
    Returns:
        Exit code (0 = success, 1 = error)
    """
    try:
        if verbose:
            print(f"Classifying inquiry: {inquiry[:50]}...")
        
        result = classify(inquiry)
        
        print(format_result(result))
        
        # Warn if low confidence
        if result.confidence < 0.5:
            print("\n⚠️  WARNING: Low confidence classification (<0.5)")
            print("    Manual review recommended")
        
        return 0
        
    except ClassificationError as e:
        print(f"\n❌ Classification failed: {str(e)}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}", file=sys.stderr)
        return 1


def classify_batch_file(file_path: str, verbose: bool = False) -> int:
    """
    Classify multiple inquiries from file (batch mode).

    Args:
        file_path: Path to file with inquiries (one per line)
        verbose: Enable verbose output

    Returns:
        Exit code (0 = success, 1 = error)
    """
    try:
        # Read inquiries from file
        input_file = Path(file_path)
        if not input_file.exists():
            print(f"\n❌ File not found: {file_path}", file=sys.stderr)
            return 1

        with open(input_file, 'r', encoding='utf-8') as f:
            inquiries = [line.strip() for line in f if line.strip()]

        if not inquiries:
            print("\n❌ No inquiries found in file", file=sys.stderr)
            return 1

        if verbose:
            print(f"Processing {len(inquiries)} inquiries in batch mode...")

        # Run batch classification
        results = asyncio.run(classify_batch(inquiries))

        # Display results
        print("\n" + "=" * 70)
        print("BATCH CLASSIFICATION RESULTS")
        print("=" * 70)
        print(f"Total Inquiries: {len(results)}")
        print()

        # Show results table
        successful = 0
        for i, result in enumerate(results, 1):
            if result.category != "Unknown":
                successful += 1

            # Truncate inquiry for display
            inquiry_display = result.inquiry[:50] + "..." if len(result.inquiry) > 50 else result.inquiry

            print(f"{i}. {inquiry_display}")
            print(f"   Category: {result.category}")
            print(f"   Subcategory: {result.subcategory}")
            print(f"   Confidence: {result.confidence:.2f}")
            print(f"   Time: {result.processing_time_ms}ms")
            print()

        # Summary
        total_time = sum(r.processing_time_ms for r in results)
        mean_time = total_time // len(results) if results else 0

        print("=" * 70)
        print("SUMMARY")
        print(f"Successful: {successful}/{len(results)}")
        print(f"Total Processing Time: {total_time}ms")
        print(f"Average Time per Inquiry: {mean_time}ms")
        print("=" * 70)

        return 0

    except Exception as e:
        print(f"\n❌ Batch processing error: {str(e)}", file=sys.stderr)
        return 1


def validate_dataset(dataset_path: str, verbose: bool = False) -> int:
    """
    Run validation against dataset.

    Args:
        dataset_path: Path to validation dataset JSON
        verbose: Enable verbose output

    Returns:
        Exit code (0 = passed quality gate, 1 = failed or error)
    """
    try:
        if verbose:
            print(f"Running validation against: {dataset_path}")

        # Run validation
        result = run_validation(dataset_path)

        # Display results
        print("\n" + "=" * 70)
        print("VALIDATION REPORT")
        print("=" * 70)
        print(f"Total Inquiries: {result.total_inquiries}")
        print(f"Correct Classifications: {result.correct_classifications}")
        print(f"Accuracy: {result.accuracy_percentage:.1f}%")
        print()

        # Per-category breakdown
        print("Per-Category Accuracy:")
        for category, stats in result.per_category_accuracy.items():
            status = "✓" if stats.accuracy >= 70.0 else "✗"
            print(f"  {status} {category}: {stats.accuracy:.1f}% ({stats.correct}/{stats.total})")
        print()

        # Processing time stats
        print("Processing Time Statistics:")
        print(f"  Min: {result.processing_time_stats.min_ms}ms")
        print(f"  Max: {result.processing_time_stats.max_ms}ms")
        print(f"  Mean: {result.processing_time_stats.mean_ms}ms")
        print(f"  P95: {result.processing_time_stats.p95_ms}ms")
        print("=" * 70)

        # Quality gate check (≥70% required)
        if result.accuracy_percentage >= 70.0:
            print(f"\n✅ PASSED: Accuracy {result.accuracy_percentage:.1f}% meets ≥70% requirement")
            return 0
        else:
            print(f"\n❌ FAILED: Accuracy {result.accuracy_percentage:.1f}% below 70% requirement")
            return 1

    except FileNotFoundError as e:
        print(f"\n❌ Dataset not found: {str(e)}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"\n❌ Invalid dataset: {str(e)}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"\n❌ Validation error: {str(e)}", file=sys.stderr)
        return 1


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="VTB Belarus Smart Support - Classification Module",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Classify single inquiry
  python -m src.cli.classify "Как открыть счет в ВТБ?"
  
  # Classify with verbose output
  python -m src.cli.classify --verbose "Какая процентная ставка по вкладу?"
  
  # Batch classification (future)
  python -m src.cli.classify --batch inquiries.txt
  
  # Run validation (future)
  python -m src.cli.classify --validate data/validation/validation_dataset.json
        """
    )
    
    # Positional argument for single inquiry
    parser.add_argument(
        "inquiry",
        nargs="?",
        type=str,
        help="Customer inquiry text to classify (Russian/Cyrillic)"
    )
    
    # Optional arguments
    parser.add_argument(
        "--batch",
        type=str,
        metavar="FILE",
        help="Batch mode: classify inquiries from file (one per line)"
    )
    
    parser.add_argument(
        "--validate",
        type=str,
        metavar="DATASET",
        help="Validation mode: test accuracy against validation dataset"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Set logging level (default: INFO)"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    
    # Determine mode
    if args.batch:
        # Batch mode
        return classify_batch_file(args.batch, verbose=args.verbose)

    elif args.validate:
        # Validation mode
        return validate_dataset(args.validate, verbose=args.verbose)
    
    elif args.inquiry:
        # Single inquiry mode
        return classify_single(args.inquiry, verbose=args.verbose)
    
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
