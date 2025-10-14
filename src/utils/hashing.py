"""
Content hashing utilities for change detection.

This module provides SHA256-based hashing for FAQ content to detect
modifications and enable incremental embedding updates.
"""

import hashlib
from typing import Optional


def compute_content_hash(question: str, answer: str, encoding: str = "utf-8") -> str:
    """
    Compute SHA256 hash of FAQ template content.

    This hash is used for change detection in incremental updates. When FAQ
    content changes, the hash will differ, triggering embedding recomputation.

    Args:
        question: Template question text (may contain Cyrillic characters)
        answer: Template answer text (may contain Cyrillic characters)
        encoding: Text encoding to use (default: utf-8 for Cyrillic support)

    Returns:
        64-character hexadecimal string (SHA256 hash)

    Example:
        >>> hash1 = compute_content_hash("Как открыть счет?", "Посетите банк.")
        >>> hash2 = compute_content_hash("Как открыть счет?", "Посетите банк.")
        >>> hash1 == hash2  # Same content = same hash
        True
        >>> hash3 = compute_content_hash("Как открыть счет?", "Другой ответ")
        >>> hash1 == hash3  # Different content = different hash
        False
    """
    # Combine question and answer with separator to avoid collision
    # e.g., Q="ab", A="c" vs Q="a", A="bc" should have different hashes
    content = f"{question}|{answer}"

    # Encode to bytes using specified encoding (UTF-8 for Cyrillic support)
    content_bytes = content.encode(encoding)

    # Compute SHA256 hash
    hash_obj = hashlib.sha256(content_bytes)

    # Return hexadecimal string representation
    return hash_obj.hexdigest()


def compute_template_hash(template: dict, question_key: str = "question", answer_key: str = "answer") -> str:
    """
    Compute content hash for a template dictionary.

    Convenience wrapper around compute_content_hash() for template dictionaries.

    Args:
        template: Dictionary containing question and answer fields
        question_key: Key for question field (default: "question")
        answer_key: Key for answer field (default: "answer")

    Returns:
        64-character hexadecimal string (SHA256 hash)

    Raises:
        KeyError: If question_key or answer_key not found in template

    Example:
        >>> template = {"question": "How to open account?", "answer": "Visit branch"}
        >>> hash_val = compute_template_hash(template)
        >>> len(hash_val)
        64
    """
    question = template[question_key]
    answer = template[answer_key]
    return compute_content_hash(question, answer)


def verify_hash(content_hash: str) -> bool:
    """
    Verify that a hash string is a valid SHA256 hash.

    Args:
        content_hash: Hash string to verify

    Returns:
        True if hash is valid SHA256 (64 hexadecimal characters), False otherwise

    Example:
        >>> verify_hash("a" * 64)  # Valid format
        True
        >>> verify_hash("abc123")  # Too short
        False
        >>> verify_hash("g" * 64)  # Invalid hex character
        False
    """
    if not isinstance(content_hash, str):
        return False

    # SHA256 produces 32 bytes = 64 hexadecimal characters
    if len(content_hash) != 64:
        return False

    # Check if all characters are valid hexadecimal
    try:
        int(content_hash, 16)
        return True
    except ValueError:
        return False


def compare_hashes(hash1: Optional[str], hash2: Optional[str]) -> bool:
    """
    Compare two content hashes for equality.

    Handles None values gracefully (useful when stored hash doesn't exist yet).

    Args:
        hash1: First hash (or None)
        hash2: Second hash (or None)

    Returns:
        True if both hashes are equal and non-None, False otherwise

    Example:
        >>> compare_hashes("abc123", "abc123")
        True
        >>> compare_hashes("abc123", "def456")
        False
        >>> compare_hashes("abc123", None)  # Missing stored hash
        False
        >>> compare_hashes(None, None)
        False
    """
    if hash1 is None or hash2 is None:
        return False
    return hash1 == hash2
