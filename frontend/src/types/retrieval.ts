/**
 * TypeScript Type Definitions for Retrieval API
 *
 * Mirrors backend/src/api/models.py RetrievalRequest, TemplateResult, and RetrievalResponse.
 * Used for type-safe API communication and frontend data handling.
 *
 * Constitution Compliance:
 * - Principle I: Modular Architecture (mirrors backend models exactly)
 * - Principle IV: API-First Integration (enables type-safe API calls)
 */

/**
 * Request payload for POST /api/retrieve
 *
 * Constructed from ClassificationResult on frontend.
 */
export interface RetrievalRequest {
  /**
   * Customer inquiry text (must match classified inquiry)
   * Must be 5-5000 characters and contain Russian text
   */
  query: string;

  /** Category from classification */
  category: string;

  /** Subcategory from classification */
  subcategory: string;

  /** Confidence score from classification (optional) */
  classification_confidence?: number;

  /**
   * Number of templates to return (1-10, default: 5)
   */
  top_k?: number;

  /**
   * Enable weighted scoring (not used in MVP)
   * @default false
   */
  use_historical_weighting?: boolean;
}

/**
 * Single retrieved template with ranking metadata
 *
 * Denormalized for UI display (includes question, answer, scores).
 */
export interface TemplateResult {
  /** Unique template identifier */
  template_id: string;

  /** FAQ question text */
  template_question: string;

  /** FAQ answer text (for copy-to-clipboard) */
  template_answer: string;

  /** Template category */
  category: string;

  /** Template subcategory */
  subcategory: string;

  /** Cosine similarity (0.0-1.0) */
  similarity_score: number;

  /** Final ranking score */
  combined_score: number;

  /** Position in result list (1=best) */
  rank: number;
}

/**
 * Response from POST /api/retrieve
 *
 * Contains ranked template results with metadata and warnings.
 */
export interface RetrievalResponse {
  /** Original inquiry (echoed back) */
  query: string;

  /** Category used for filtering */
  category: string;

  /** Subcategory used for filtering */
  subcategory: string;

  /** Ranked template results (max 10) */
  results: TemplateResult[];

  /** Number of templates in category before ranking */
  total_candidates: number;

  /** Time to embed query + rank (ms) */
  processing_time_ms: number;

  /** When retrieval completed (ISO 8601 UTC) */
  timestamp: string;

  /** Warnings (e.g., low confidence, no templates) */
  warnings: string[];
}

/**
 * Health check response for GET /api/health
 *
 * Used by frontend to detect service availability.
 */
export interface HealthResponse {
  /** Overall health status */
  status: 'healthy' | 'unhealthy';

  /** Whether classification service can handle requests */
  classification_available: boolean;

  /** Whether retrieval service can handle requests */
  retrieval_available: boolean;

  /** Number of FAQ templates in embeddings database */
  embeddings_count: number;
}

/**
 * Type guard to check if health status is healthy
 */
export function isHealthy(health: HealthResponse): boolean {
  return (
    health.status === 'healthy' &&
    health.classification_available &&
    health.retrieval_available &&
    health.embeddings_count > 0
  );
}

/**
 * Validation helper: Check if retrieval request is valid
 *
 * @param request - Request to validate
 * @returns Error message if invalid, null if valid
 */
export function validateRetrievalRequest(request: RetrievalRequest): string | null {
  const trimmedQuery = request.query.trim();

  if (trimmedQuery.length < 5) {
    return "Query must be at least 5 characters";
  }

  if (trimmedQuery.length > 5000) {
    return "Query must not exceed 5000 characters";
  }

  if (!request.category || request.category.trim().length === 0) {
    return "Category is required";
  }

  if (!request.subcategory || request.subcategory.trim().length === 0) {
    return "Subcategory is required";
  }

  if (request.top_k !== undefined) {
    if (request.top_k < 1) {
      return "Number of results must be at least 1";
    }
    if (request.top_k > 10) {
      return "Number of results must not exceed 10";
    }
  }

  if (request.classification_confidence !== undefined) {
    if (request.classification_confidence < 0.0 || request.classification_confidence > 1.0) {
      return "Classification confidence must be between 0.0 and 1.0";
    }
  }

  return null; // Valid
}
