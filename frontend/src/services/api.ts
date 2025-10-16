/**
 * Axios HTTP Client Configuration
 *
 * Provides configured Axios instance for Smart Support API communication.
 * Includes interceptors for error handling, request/response logging, and timeout management.
 *
 * Constitution Compliance:
 * - Principle II: User-Centric Design (user-friendly error messages)
 * - Principle IV: API-First Integration (type-safe API communication)
 */

import axios from 'axios';
import type { AxiosError, AxiosInstance, InternalAxiosRequestConfig, AxiosResponse } from 'axios';
import type { ErrorResponse } from '../types/classification';
import { isErrorResponse } from '../types/classification';

/**
 * Base API URL
 *
 * In development, Vite proxy will route /api/* to http://localhost:8000/api/*
 * In production, this will be the actual backend URL
 */
const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

/**
 * Request timeout values aligned with API performance requirements
 * - Classification: 30000ms (increased to accommodate expanded prompt with all examples)
 * - Retrieval: 2000ms (FR-010 requires <1s, add 1s buffer)
 * - Default: 5000ms for health checks and other endpoints
 */
export const API_TIMEOUTS = {
  CLASSIFICATION: 30000,
  RETRIEVAL: 2000,
  DEFAULT: 5000,
} as const;

/**
 * Create configured Axios instance
 */
const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: API_TIMEOUTS.DEFAULT,
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Request interceptor
 *
 * Logs outgoing requests and adds custom headers if needed.
 */
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // Log request in development
    if (import.meta.env.DEV) {
      console.log(`[API Request] ${config.method?.toUpperCase()} ${config.url}`, {
        data: config.data,
        params: config.params,
      });
    }

    // Add timestamp to track request duration
    config.metadata = { startTime: Date.now() };

    return config;
  },
  (error) => {
    console.error('[API Request Error]', error);
    return Promise.reject(error);
  }
);

/**
 * Response interceptor
 *
 * Logs responses, calculates request duration, and transforms error responses.
 */
apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    // Calculate request duration
    const startTime = response.config.metadata?.startTime;
    const duration = startTime ? Date.now() - startTime : 0;

    // Log response in development
    if (import.meta.env.DEV) {
      console.log(
        `[API Response] ${response.config.method?.toUpperCase()} ${response.config.url}`,
        {
          status: response.status,
          duration: `${duration}ms`,
          data: response.data,
        }
      );
    }

    // Warn if request exceeded expected duration
    if (response.config.url?.includes('/classify') && duration > 2000) {
      console.warn(`Classification took ${duration}ms (expected <2000ms)`);
    } else if (response.config.url?.includes('/retrieve') && duration > 1000) {
      console.warn(`Retrieval took ${duration}ms (expected <1000ms)`);
    }

    return response;
  },
  (error: AxiosError) => {
    // Handle error responses
    return handleApiError(error);
  }
);

/**
 * Handle API errors and transform to user-friendly format
 *
 * @param error - Axios error object
 * @returns Rejected promise with ErrorResponse
 */
function handleApiError(error: AxiosError): Promise<ErrorResponse> {
  const startTime = error.config?.metadata?.startTime;
  const duration = startTime ? Date.now() - startTime : 0;

  // Log error in development
  if (import.meta.env.DEV) {
    console.error(
      `[API Error] ${error.config?.method?.toUpperCase()} ${error.config?.url}`,
      {
        status: error.response?.status,
        duration: `${duration}ms`,
        message: error.message,
        data: error.response?.data,
      }
    );
  }

  // If response has ErrorResponse format, use it directly
  if (error.response?.data && isErrorResponse(error.response.data)) {
    return Promise.reject(error.response.data);
  }

  // FastAPI wraps error in "detail" field - check there too
  if (error.response?.data && typeof error.response.data === 'object' && 'detail' in error.response.data) {
    const detail = (error.response.data as { detail: unknown }).detail;
    if (detail && typeof detail === 'object' && isErrorResponse(detail)) {
      return Promise.reject(detail);
    }
  }

  // Create user-friendly error based on error type
  let errorResponse: ErrorResponse;

  if (error.code === 'ECONNABORTED' || error.message.includes('timeout')) {
    // Timeout error
    errorResponse = {
      error: 'Request timed out. Please try again.',
      error_type: 'timeout',
      details: error.message,
      timestamp: new Date().toISOString(),
    };
  } else if (!error.response) {
    // Network error (no response from server)
    errorResponse = {
      error: 'Cannot connect to server. Please check your internet connection.',
      error_type: 'api_error',
      details: error.message,
      timestamp: new Date().toISOString(),
    };
  } else if (error.response.status >= 500) {
    // Server error (5xx)
    errorResponse = {
      error: 'Server error occurred. Please try again or contact support.',
      error_type: 'api_error',
      details: `HTTP ${error.response.status}: ${error.message}`,
      timestamp: new Date().toISOString(),
    };
  } else if (error.response.status === 400) {
    // Validation error (400)
    const errorMessage =
      typeof error.response.data === 'object' && error.response.data !== null && 'detail' in error.response.data
        ? String((error.response.data as { detail: unknown }).detail)
        : 'Invalid request. Please check your input.';

    errorResponse = {
      error: errorMessage,
      error_type: 'validation',
      details: error.message,
      timestamp: new Date().toISOString(),
    };
  } else {
    // Other client errors (4xx)
    errorResponse = {
      error: 'An error occurred. Please try again.',
      error_type: 'unknown',
      details: `HTTP ${error.response.status}: ${error.message}`,
      timestamp: new Date().toISOString(),
    };
  }

  return Promise.reject(errorResponse);
}

/**
 * Extend Axios config to include metadata
 */
declare module 'axios' {
  export interface InternalAxiosRequestConfig {
    metadata?: {
      startTime: number;
    };
  }
}

export default apiClient;
