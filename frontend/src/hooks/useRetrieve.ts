/**
 * useRetrieve Hook
 *
 * React Query hook for retrieving template responses.
 *
 * Features:
 * - Automatic error handling
 * - Loading states
 * - Type-safe responses
 */

import { useMutation } from '@tanstack/react-query';
import { retrieveTemplates } from '../services/retrievalService';
import type { RetrievalRequest, RetrievalResponse } from '../types/retrieval';
import type { ErrorResponse } from '../types/classification';

export function useRetrieve() {
  return useMutation<RetrievalResponse, ErrorResponse, RetrievalRequest>({
    mutationFn: retrieveTemplates,
  });
}
