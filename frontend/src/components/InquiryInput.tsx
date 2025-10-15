/**
 * InquiryInput Component
 *
 * Text input area for customer inquiry submission.
 * Validates Russian text (Cyrillic required, 5-5000 characters).
 *
 * Features:
 * - Multi-line textarea with character counter
 * - Real-time validation feedback
 * - Submit button with loading state
 * - User-friendly error messages
 */

import { useState } from 'react';
import { validateInquiry } from '../types/classification';

interface InquiryInputProps {
  /** Callback when valid inquiry is submitted */
  onSubmit: (inquiry: string) => void;
  /** Whether classification is in progress */
  isLoading?: boolean;
  /** Disabled state (e.g., when retrieval is running) */
  disabled?: boolean;
}

export function InquiryInput({ onSubmit, isLoading = false, disabled = false }: InquiryInputProps) {
  const [inquiry, setInquiry] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [touched, setTouched] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    // Validate inquiry
    const validationError = validateInquiry(inquiry);

    if (validationError) {
      setError(validationError);
      setTouched(true);
      return;
    }

    // Clear error and submit
    setError(null);
    onSubmit(inquiry.trim());
  };

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value;
    setInquiry(value);

    // Clear error when user starts typing
    if (error && touched) {
      setError(null);
    }
  };

  const handleBlur = () => {
    setTouched(true);

    // Validate on blur if there's text
    if (inquiry.trim().length > 0) {
      const validationError = validateInquiry(inquiry);
      setError(validationError);
    }
  };

  const characterCount = inquiry.length;
  const isOverLimit = characterCount > 5000;
  const isUnderLimit = characterCount > 0 && characterCount < 5;
  const showError = touched && error;

  return (
    <form onSubmit={handleSubmit} className="w-full">
      <div className="space-y-4">
        {/* Label */}
        <label htmlFor="inquiry" className="block text-sm font-medium text-gray-700">
          Введите обращение клиента
        </label>

        {/* Textarea */}
        <div className="relative">
          <textarea
            id="inquiry"
            value={inquiry}
            onChange={handleChange}
            onBlur={handleBlur}
            disabled={disabled || isLoading}
            placeholder="Например: Как заблокировать банковскую карту, если она утеряна?"
            rows={6}
            className={`
              w-full px-4 py-3 border rounded-lg resize-none
              focus:outline-none focus:ring-2 focus:ring-blue-500
              disabled:bg-gray-100 disabled:cursor-not-allowed
              ${showError ? 'border-red-500' : 'border-gray-300'}
              ${isOverLimit ? 'border-red-500' : ''}
            `}
          />

          {/* Character counter */}
          <div className={`
            absolute bottom-3 right-3 text-xs
            ${isOverLimit ? 'text-red-600 font-semibold' : 'text-gray-500'}
            ${isUnderLimit ? 'text-orange-600' : ''}
          `}>
            {characterCount} / 5000
          </div>
        </div>

        {/* Error message */}
        {showError && (
          <div className="flex items-start space-x-2 text-red-600 text-sm">
            <svg className="w-5 h-5 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
            <span>{error}</span>
          </div>
        )}

        {/* Submit button */}
        <button
          type="submit"
          disabled={disabled || isLoading || characterCount === 0}
          className={`
            w-full px-6 py-3 rounded-lg font-medium
            transition-colors duration-200
            focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
            ${
              disabled || isLoading || characterCount === 0
                ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                : 'bg-blue-600 text-white hover:bg-blue-700'
            }
          `}
        >
          {isLoading ? (
            <span className="flex items-center justify-center space-x-2">
              <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              <span>Классификация...</span>
            </span>
          ) : (
            'Классифицировать обращение'
          )}
        </button>

        {/* Helper text */}
        <p className="text-xs text-gray-500">
          Введите текст обращения на русском языке (минимум 5 символов)
        </p>
      </div>
    </form>
  );
}
