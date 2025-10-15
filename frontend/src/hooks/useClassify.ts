/**
 * useClassify Hook
 *
 * React Query hook for classifying customer inquiries.
 *
 * Features:
 * - Automatic error handling
 * - Loading states
 * - Type-safe responses
 */

import { useMutation } from '@tanstack/react-query';
import { classifyInquiry } from '../services/classificationService';
import type { ClassificationResult, ErrorResponse } from '../types/classification';

export function useClassify() {
  return useMutation<ClassificationResult, ErrorResponse, string>({
    mutationFn: classifyInquiry,
  });
}
