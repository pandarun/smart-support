"""
Classification Module - Core Classifier

Main classification logic for single and batch inquiry processing.
Coordinates FAQ parsing, prompt building, API calls, and result validation.

Constitution Compliance:
- Principle I: Modular Architecture (coordinates components)
- QR-001: ≥70% accuracy on validation dataset
- PR-001: <2 seconds response time (95th percentile)
"""

import json
import time
import asyncio
from typing import Optional
from datetime import datetime

from src.classification.models import ClassificationRequest, ClassificationResult
from src.classification.faq_parser import get_faq_parser, FAQParser
from src.classification.prompt_builder import PromptBuilder
from src.classification.client import get_scibox_client, SciboxClient, SciboxAPIError
from src.utils.logging import get_logger, log_classification, log_error
from src.utils.validation import validate_inquiry_text, sanitize_inquiry


class ClassificationError(Exception):
    """Exception raised when classification fails."""
    pass


class Classifier:
    """
    Main classifier for customer inquiries.
    
    Coordinates FAQ parsing, prompt construction, LLM API calls,
    and result validation.
    """
    
    def __init__(
        self,
        faq_parser: Optional[FAQParser] = None,
        scibox_client: Optional[SciboxClient] = None
    ):
        """
        Initialize classifier.
        
        Args:
            faq_parser: FAQ parser instance (uses cached instance if not provided)
            scibox_client: Scibox client instance (uses cached instance if not provided)
        """
        self.logger = get_logger()
        self.faq_parser = faq_parser or get_faq_parser()
        self.scibox_client = scibox_client or get_scibox_client()
        
        # Initialize prompt builder with FAQ categories
        categories = self.faq_parser.get_all_categories_dict()
        self.prompt_builder = PromptBuilder(categories)
        
        self.logger.info(
            f"Classifier initialized with {self.faq_parser.get_category_count()} categories, "
            f"{self.faq_parser.get_subcategory_count()} subcategories"
        )
    
    def classify(self, inquiry: str) -> ClassificationResult:
        """
        Classify a single customer inquiry.
        
        Args:
            inquiry: Customer inquiry text in Russian
            
        Returns:
            ClassificationResult with category, subcategory, confidence
            
        Raises:
            ClassificationError: If classification fails
        """
        start_time = time.time()
        
        try:
            # Step 1: Validate input
            sanitized = sanitize_inquiry(inquiry)
            is_valid, error_msg = validate_inquiry_text(sanitized)
            if not is_valid:
                raise ClassificationError(error_msg)
            
            # Step 2: Build prompt
            messages = self.prompt_builder.build_classification_messages(sanitized)
            
            # Step 3: Call Scibox API
            try:
                completion = self.scibox_client.chat_completion(
                    messages=messages,
                    temperature=0.0,  # Deterministic mode (QR-002)
                    max_tokens=150
                )
            except SciboxAPIError as e:
                log_error(str(e), "api_error")
                raise ClassificationError(str(e)) from e
            
            # Step 4: Parse JSON response
            response_text = completion.choices[0].message.content
            try:
                response_data = json.loads(response_text)
            except json.JSONDecodeError as e:
                log_error(
                    "Failed to parse LLM response as JSON",
                    "api_error",
                    details=response_text
                )
                raise ClassificationError(
                    "Classification service returned invalid data. Please contact support."
                ) from e
            
            # Step 5: Extract classification data
            category = response_data.get("category", "")
            subcategory = response_data.get("subcategory", "")
            confidence = float(response_data.get("confidence", 0.0))
            
            # Step 6: Validate category/subcategory against FAQ
            if not self.faq_parser.is_valid_category(category):
                self.logger.warning(
                    f"LLM returned invalid category: {category}. "
                    "Attempting to find closest match..."
                )
                # In production, could implement fuzzy matching here
                # For now, use first category as fallback
                category = self.faq_parser.get_categories()[0]
                subcategory = self.faq_parser.get_subcategories(category)[0]
                confidence = max(0.3, confidence * 0.5)  # Reduce confidence for fallback
            elif not self.faq_parser.is_valid_subcategory(category, subcategory):
                self.logger.warning(
                    f"LLM returned invalid subcategory '{subcategory}' for category '{category}'"
                )
                # Use first subcategory of the category as fallback
                subcategory = self.faq_parser.get_subcategories(category)[0]
                confidence = max(0.4, confidence * 0.7)  # Reduce confidence slightly
            
            # Step 7: Calculate processing time
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            # Step 8: Create result
            result = ClassificationResult(
                inquiry=sanitized,
                category=category,
                subcategory=subcategory,
                confidence=confidence,
                processing_time_ms=processing_time_ms,
                timestamp=datetime.utcnow().isoformat() + "Z"
            )
            
            # Step 9: Log classification
            log_classification(
                inquiry=sanitized,
                category=category,
                subcategory=subcategory,
                confidence=confidence,
                processing_time_ms=processing_time_ms
            )
            
            return result
            
        except ClassificationError:
            raise
        except Exception as e:
            log_error(f"Unexpected error during classification: {str(e)}", "unknown")
            raise ClassificationError(
                f"Classification failed: {str(e)}"
            ) from e
    
    async def classify_async(self, inquiry: str) -> ClassificationResult:
        """
        Async version of classify for batch processing.
        
        Args:
            inquiry: Customer inquiry text
            
        Returns:
            ClassificationResult
        """
        # Run synchronous classify in thread pool
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.classify, inquiry)
    
    async def classify_batch(self, inquiries: list[str]) -> list[ClassificationResult]:
        """
        Classify multiple inquiries in parallel.
        
        Args:
            inquiries: List of inquiry texts
            
        Returns:
            List of ClassificationResults in same order as input
            
        Raises:
            ClassificationError: If batch validation fails
        """
        if not inquiries:
            raise ClassificationError("Batch must contain at least one inquiry")
        
        if len(inquiries) > 100:
            raise ClassificationError("Batch size must not exceed 100 inquiries")
        
        self.logger.info(f"Starting batch classification for {len(inquiries)} inquiries")
        
        # Create async tasks for parallel processing
        tasks = [self.classify_async(inquiry) for inquiry in inquiries]
        
        # Gather results (maintains input order)
        # return_exceptions=True allows partial failures
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions, convert to results
        successful_results = []
        failed_count = 0
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(f"Failed to classify inquiry {i}: {str(result)}")
                failed_count += 1
                # For failed inquiries, create error result with placeholder values
                successful_results.append(
                    ClassificationResult(
                        inquiry=inquiries[i][:100],
                        category="Unknown",
                        subcategory="Unknown",
                        confidence=0.0,
                        processing_time_ms=0
                    )
                )
            else:
                successful_results.append(result)
        
        self.logger.info(
            f"Batch classification completed: {len(successful_results) - failed_count} "
            f"successful, {failed_count} failed"
        )
        
        return successful_results


# Global classifier instance (cached)
_classifier_instance: Optional[Classifier] = None


def get_classifier() -> Classifier:
    """
    Get cached classifier instance.
    
    Returns:
        Cached Classifier instance
    """
    global _classifier_instance
    
    if _classifier_instance is None:
        _classifier_instance = Classifier()
    
    return _classifier_instance


def classify(inquiry: str) -> ClassificationResult:
    """
    Convenience function to classify a single inquiry.
    
    Args:
        inquiry: Customer inquiry text
        
    Returns:
        ClassificationResult
    """
    classifier = get_classifier()
    return classifier.classify(inquiry)


async def classify_batch(inquiries: list[str]) -> list[ClassificationResult]:
    """
    Convenience function to classify multiple inquiries in batch.
    
    Args:
        inquiries: List of inquiry texts
        
    Returns:
        List of ClassificationResults
    """
    classifier = get_classifier()
    return await classifier.classify_batch(inquiries)
