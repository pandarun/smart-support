export interface ClassificationRequest {
  inquiry: string;
}

export interface ClassificationResult {
  inquiry: string;
  category: string;
  subcategory: string;
  confidence: number;
  processing_time_ms: number;
  timestamp: string;
}

export interface ErrorResponse {
  error: string;
  error_type: 'validation' | 'api_error' | 'timeout' | 'unknown';
  details?: string;
  timestamp: string;
}

export function isErrorResponse(obj: unknown): obj is ErrorResponse {
  return (
    typeof obj === 'object' &&
    obj !== null &&
    'error' in obj &&
    'error_type' in obj
  );
}

export function validateInquiry(inquiry: string): string | null {
  const trimmed = inquiry.trim();

  if (trimmed.length < 5) {
    return "Inquiry must be at least 5 characters";
  }

  if (trimmed.length > 5000) {
    return "Inquiry must not exceed 5000 characters";
  }

  const hasCyrillic = /[а-яА-ЯёЁ]/.test(trimmed);
  if (!hasCyrillic) {
    return "Please enter inquiry in Russian (Cyrillic characters required)";
  }

  return null;
}
