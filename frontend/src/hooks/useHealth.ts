/**
 * useHealth Hook
 *
 * React Query hook for checking API health status.
 *
 * Features:
 * - Automatic polling (optional)
 * - Type-safe responses
 * - Ready/degraded status detection
 */

import { useQuery } from '@tanstack/react-query';
import { checkHealth } from '../services/retrievalService';
import type { HealthResponse } from '../types/retrieval';

export function useHealth(options?: { refetchInterval?: number }) {
  return useQuery<HealthResponse>({
    queryKey: ['health'],
    queryFn: checkHealth,
    refetchInterval: options?.refetchInterval,
    // Don't retry on failure (health check)
    retry: false,
  });
}
