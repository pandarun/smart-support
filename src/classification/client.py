"""
Classification Module - Scibox API Client

Wrapper for Scibox LLM API using OpenAI-compatible interface.
Handles authentication, timeout, error handling, and retry logic.

Constitution Compliance:
- Principle IV: API-First Integration (Scibox LLM service)
- Performance: <2s response time with 1.8s timeout
"""

import os
import time
from typing import Dict, Any, Optional
from openai import OpenAI, APIError, APIConnectionError, APITimeoutError
from openai.types.chat import ChatCompletion


class SciboxAPIError(Exception):
    """Base exception for Scibox API errors."""
    pass


class SciboxClient:
    """
    Scibox API client wrapper.
    
    Provides classification and embedding capabilities using Scibox LLM service.
    """
    
    # Scibox API configuration
    BASE_URL = "https://llm.t1v.scibox.tech/v1"
    CHAT_MODEL = "Qwen2.5-72B-Instruct-AWQ"
    EMBEDDING_MODEL = "bge-m3"
    
    def __init__(
        self, 
        api_key: Optional[str] = None,
        timeout: float = 1.8,
        max_retries: int = 0
    ):
        """
        Initialize Scibox API client.
        
        Args:
            api_key: Scibox API key (uses SCIBOX_API_KEY env var if not provided)
            timeout: Request timeout in seconds (default: 1.8s)
            max_retries: Maximum retry attempts for transient failures (default: 0)
            
        Raises:
            ValueError: If API key not provided and SCIBOX_API_KEY env var not set
        """
        if api_key is None:
            api_key = os.getenv("SCIBOX_API_KEY")
        
        if not api_key:
            raise ValueError(
                "Scibox API key not provided. "
                "Set SCIBOX_API_KEY environment variable or pass api_key parameter."
            )
        
        self.timeout = timeout
        self.max_retries = max_retries
        
        # Initialize OpenAI client with Scibox configuration
        self.client = OpenAI(
            api_key=api_key,
            base_url=self.BASE_URL,
            timeout=timeout,
            max_retries=max_retries
        )
    
    def chat_completion(
        self,
        messages: list[Dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int = 150,
        response_format: Optional[Dict[str, str]] = None
    ) -> ChatCompletion:
        """
        Create chat completion using Scibox LLM.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature (0.0 = deterministic)
            max_tokens: Maximum tokens in response
            response_format: Optional response format specification
            
        Returns:
            ChatCompletion object from OpenAI API
            
        Raises:
            SciboxAPIError: If API request fails
        """
        try:
            start_time = time.time()
            
            completion = self.client.chat.completions.create(
                model=self.CHAT_MODEL,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            elapsed_ms = int((time.time() - start_time) * 1000)
            
            return completion
            
        except APITimeoutError as e:
            raise SciboxAPIError(
                "Classification timed out. Please retry."
            ) from e
        except APIConnectionError as e:
            raise SciboxAPIError(
                "Classification service unavailable. Please retry."
            ) from e
        except APIError as e:
            raise SciboxAPIError(
                f"Classification service error: {str(e)}"
            ) from e
        except Exception as e:
            raise SciboxAPIError(
                f"Unexpected error during classification: {str(e)}"
            ) from e
    
    def create_embedding(self, text: str) -> list[float]:
        """
        Create text embedding using Scibox embedding model.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector as list of floats
            
        Raises:
            SciboxAPIError: If API request fails
        """
        try:
            response = self.client.embeddings.create(
                model=self.EMBEDDING_MODEL,
                input=text
            )
            
            return response.data[0].embedding
            
        except APITimeoutError as e:
            raise SciboxAPIError(
                "Embedding request timed out. Please retry."
            ) from e
        except APIConnectionError as e:
            raise SciboxAPIError(
                "Embedding service unavailable. Please retry."
            ) from e
        except APIError as e:
            raise SciboxAPIError(
                f"Embedding service error: {str(e)}"
            ) from e
        except Exception as e:
            raise SciboxAPIError(
                f"Unexpected error during embedding: {str(e)}"
            ) from e
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check Scibox API health and connectivity.
        
        Returns:
            Dictionary with status information
        """
        try:
            # Test with simple completion
            response = self.client.chat.completions.create(
                model=self.CHAT_MODEL,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5
            )
            
            return {
                "status": "healthy",
                "model": self.CHAT_MODEL,
                "base_url": self.BASE_URL
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "base_url": self.BASE_URL
            }


# Global client instance (cached)
_client_instance: Optional[SciboxClient] = None


def get_scibox_client(
    api_key: Optional[str] = None,
    timeout: Optional[float] = None,
    max_retries: Optional[int] = None
) -> SciboxClient:
    """
    Get cached Scibox client instance.

    Args:
        api_key: Scibox API key (optional)
        timeout: Request timeout (optional, uses API_TIMEOUT env var or 1.8s default)
        max_retries: Maximum retry attempts (optional, default: 3 for production)

    Returns:
        Cached SciboxClient instance

    Note:
        The OpenAI client automatically implements exponential backoff for retries:
        - 1st retry: ~2 seconds delay
        - 2nd retry: ~4 seconds delay
        - 3rd retry: ~8 seconds delay

        Retries are triggered for:
        - Connection errors (APIConnectionError)
        - Rate limit errors (HTTP 429)
        - Server errors (HTTP 5xx)
        - Request timeout errors
    """
    global _client_instance

    if _client_instance is None:
        if timeout is None:
            timeout = float(os.getenv("API_TIMEOUT", "1.8"))

        if max_retries is None:
            # Default: 3 retries for production (exponential backoff)
            # Set to 0 for development/testing to fail fast
            max_retries = int(os.getenv("API_MAX_RETRIES", "3"))

        _client_instance = SciboxClient(
            api_key=api_key,
            timeout=timeout,
            max_retries=max_retries
        )

    return _client_instance
