/**
 * Classification API Service
 *
 * Provides functions for interacting with the classification API endpoint.
 */

import apiClient, { API_TIMEOUTS } from './api';
import type {
  ClassificationRequest,
  ClassificationResult,
  ErrorResponse,
} from '../types/classification';

/**
 * Classify a customer inquiry
 *
 * POST /api/classify
 *
 * @param inquiry - Customer inquiry text in Russian
 * @returns Classification result with category, subcategory, and confidence
 * @throws ErrorResponse if classification fails
 */
export async function classifyInquiry(inquiry: string): Promise<ClassificationResult> {
  const request: ClassificationRequest = { inquiry };

  const response = await apiClient.post<ClassificationResult>(
    '/classify',
    request,
    {
      timeout: API_TIMEOUTS.CLASSIFICATION, // 3 seconds
    }
  );

  return response.data;
}
