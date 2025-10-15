/**
 * Retrieval API Service
 *
 * Provides functions for interacting with the retrieval API endpoint.
 */

import apiClient, { API_TIMEOUTS } from './api';
import type {
  RetrievalRequest,
  RetrievalResponse,
  HealthResponse,
} from '../types/retrieval';

/**
 * Retrieve template responses for a classified inquiry
 *
 * POST /api/retrieve
 *
 * @param request - Retrieval request with query, category, subcategory
 * @returns Retrieval response with ranked template results
 * @throws ErrorResponse if retrieval fails
 */
export async function retrieveTemplates(request: RetrievalRequest): Promise<RetrievalResponse> {
  const response = await apiClient.post<RetrievalResponse>(
    '/retrieve',
    request,
    {
      timeout: API_TIMEOUTS.RETRIEVAL, // 2 seconds
    }
  );

  return response.data;
}

/**
 * Check API health status
 *
 * GET /api/health
 *
 * @returns Health status with service availability
 */
export async function checkHealth(): Promise<HealthResponse> {
  const response = await apiClient.get<HealthResponse>('/health', {
    timeout: API_TIMEOUTS.DEFAULT, // 5 seconds
  });

  return response.data;
}
