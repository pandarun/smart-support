"""
Classification Module - Validator

Runs validation against ground truth datasets and generates accuracy reports.

Constitution Compliance:
- Principle III: Data-Driven Validation
- QR-001: ≥70% accuracy requirement
"""

import json
from pathlib import Path
from typing import Dict, List
from collections import defaultdict
import statistics

from src.classification.models import (
    ValidationRecord,
    ValidationResult,
    CategoryAccuracy,
    ProcessingTimeStats
)
from src.classification.classifier import get_classifier, ClassificationError
from src.utils.logging import get_logger, log_validation


class Validator:
    """
    Validates classification accuracy against ground truth dataset.
    """
    
    def __init__(self):
        """Initialize validator."""
        self.logger = get_logger()
        self.classifier = get_classifier()
    
    def load_validation_dataset(self, dataset_path: str) -> List[ValidationRecord]:
        """
        Load validation dataset from JSON file.
        
        Args:
            dataset_path: Path to validation dataset JSON
            
        Returns:
            List of ValidationRecord objects
            
        Raises:
            FileNotFoundError: If dataset file not found
            ValueError: If dataset format is invalid
        """
        dataset_file = Path(dataset_path)
        
        if not dataset_file.exists():
            raise FileNotFoundError(f"Validation dataset not found: {dataset_path}")
        
        try:
            with open(dataset_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not isinstance(data, list):
                raise ValueError("Dataset must be a JSON array")
            
            records = []
            for i, item in enumerate(data):
                try:
                    record = ValidationRecord(**item)
                    records.append(record)
                except Exception as e:
                    self.logger.warning(f"Skipping invalid record {i}: {str(e)}")
            
            if not records:
                raise ValueError("No valid records found in dataset")
            
            self.logger.info(f"Loaded {len(records)} validation records from {dataset_path}")
            return records
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in dataset file: {str(e)}")
        except Exception as e:
            if isinstance(e, (FileNotFoundError, ValueError)):
                raise
            raise ValueError(f"Failed to load validation dataset: {str(e)}")
    
    def run_validation(self, dataset_path: str) -> ValidationResult:
        """
        Run validation against dataset.
        
        Args:
            dataset_path: Path to validation dataset JSON
            
        Returns:
            ValidationResult with accuracy metrics
        """
        self.logger.info(f"Starting validation run: {dataset_path}")
        
        # Load dataset
        records = self.load_validation_dataset(dataset_path)
        
        # Classify each inquiry and compare to ground truth
        correct_count = 0
        processing_times = []
        category_stats = defaultdict(lambda: {"total": 0, "correct": 0})
        
        for i, record in enumerate(records):
            try:
                # Classify inquiry
                result = self.classifier.classify(record.inquiry)
                processing_times.append(result.processing_time_ms)
                
                # Track per-category stats
                category_stats[record.expected_category]["total"] += 1
                
                # Check if classification is correct
                is_correct = (
                    result.category == record.expected_category and
                    result.subcategory == record.expected_subcategory
                )
                
                if is_correct:
                    correct_count += 1
                    category_stats[record.expected_category]["correct"] += 1
                else:
                    self.logger.info(
                        f"Misclassification: '{record.inquiry[:50]}...' "
                        f"Expected: {record.expected_category}/{record.expected_subcategory}, "
                        f"Got: {result.category}/{result.subcategory}"
                    )
                
            except ClassificationError as e:
                self.logger.error(f"Failed to classify record {i}: {str(e)}")
                processing_times.append(0)
                category_stats[record.expected_category]["total"] += 1
        
        # Calculate overall accuracy
        total_count = len(records)
        accuracy_percentage = (correct_count / total_count * 100) if total_count > 0 else 0.0
        
        # Calculate per-category accuracy
        per_category_accuracy = {}
        for category, stats in category_stats.items():
            cat_accuracy = (stats["correct"] / stats["total"] * 100) if stats["total"] > 0 else 0.0
            per_category_accuracy[category] = CategoryAccuracy(
                total=stats["total"],
                correct=stats["correct"],
                accuracy=cat_accuracy
            )
        
        # Calculate processing time stats
        valid_times = [t for t in processing_times if t > 0]
        processing_time_stats = self._calculate_time_stats(valid_times)
        
        # Create validation result
        validation_result = ValidationResult(
            total_inquiries=total_count,
            correct_classifications=correct_count,
            accuracy_percentage=accuracy_percentage,
            per_category_accuracy=per_category_accuracy,
            processing_time_stats=processing_time_stats
        )
        
        # Log validation summary
        log_validation(
            total=total_count,
            correct=correct_count,
            accuracy=accuracy_percentage,
            processing_time_ms=sum(valid_times)
        )
        
        # Save results to file
        self._save_validation_results(validation_result, dataset_path)
        
        return validation_result
    
    def _calculate_time_stats(self, times: List[int]) -> ProcessingTimeStats:
        """
        Calculate processing time statistics.
        
        Args:
            times: List of processing times in milliseconds
            
        Returns:
            ProcessingTimeStats object
        """
        if not times:
            return ProcessingTimeStats(min_ms=0, max_ms=0, mean_ms=0, p95_ms=0)
        
        min_time = min(times)
        max_time = max(times)
        mean_time = int(statistics.mean(times))
        
        # Calculate P95 (95th percentile)
        sorted_times = sorted(times)
        p95_index = int(len(sorted_times) * 0.95)
        p95_time = sorted_times[p95_index] if p95_index < len(sorted_times) else sorted_times[-1]
        
        return ProcessingTimeStats(
            min_ms=min_time,
            max_ms=max_time,
            mean_ms=mean_time,
            p95_ms=p95_time
        )
    
    def _save_validation_results(self, result: ValidationResult, dataset_path: str) -> None:
        """
        Save validation results to JSON file.
        
        Args:
            result: ValidationResult to save
            dataset_path: Original dataset path (used to determine output path)
        """
        # Create output filename based on input
        dataset_name = Path(dataset_path).stem
        output_path = Path("data/results") / f"{dataset_name}_results.json"
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert result to dict for JSON serialization
        result_dict = result.model_dump()
        
        # Save to file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result_dict, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Validation results saved to: {output_path}")


# Global validator instance
_validator_instance = None


def get_validator() -> Validator:
    """Get cached validator instance."""
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = Validator()
    return _validator_instance


def run_validation(dataset_path: str) -> ValidationResult:
    """
    Convenience function to run validation.
    
    Args:
        dataset_path: Path to validation dataset JSON
        
    Returns:
        ValidationResult with accuracy metrics
    """
    validator = get_validator()
    return validator.run_validation(dataset_path)
