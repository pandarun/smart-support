/**
 * ErrorDisplay Component
 *
 * User-friendly error message display with retry functionality.
 *
 * Features:
 * - Different error types with appropriate icons
 * - Retry button for recoverable errors
 * - Dismissible
 * - Accessible design
 */

import type { ErrorResponse } from '../types/classification';

interface ErrorDisplayProps {
  /** Error to display */
  error: ErrorResponse;
  /** Optional retry callback */
  onRetry?: () => void;
  /** Optional dismiss callback */
  onDismiss?: () => void;
}

export function ErrorDisplay({ error, onRetry, onDismiss }: ErrorDisplayProps) {
  // Get icon and colors based on error type
  const getErrorStyle = (errorType: string) => {
    switch (errorType) {
      case 'validation':
        return {
          icon: (
            <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
          ),
          bgColor: 'bg-yellow-50',
          borderColor: 'border-yellow-300',
          iconColor: 'text-yellow-600',
          textColor: 'text-yellow-800',
          title: 'Ошибка валидации',
        };
      case 'timeout':
        return {
          icon: (
            <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
            </svg>
          ),
          bgColor: 'bg-orange-50',
          borderColor: 'border-orange-300',
          iconColor: 'text-orange-600',
          textColor: 'text-orange-800',
          title: 'Превышено время ожидания',
        };
      case 'api_error':
        return {
          icon: (
            <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
          ),
          bgColor: 'bg-red-50',
          borderColor: 'border-red-300',
          iconColor: 'text-red-600',
          textColor: 'text-red-800',
          title: 'Ошибка сервиса',
        };
      default:
        return {
          icon: (
            <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
          ),
          bgColor: 'bg-red-50',
          borderColor: 'border-red-300',
          iconColor: 'text-red-600',
          textColor: 'text-red-800',
          title: 'Произошла ошибка',
        };
    }
  };

  const style = getErrorStyle(error.error_type);
  const canRetry = error.error_type === 'timeout' || error.error_type === 'api_error';

  return (
    <div className={`${style.bgColor} border ${style.borderColor} rounded-lg p-4 shadow-sm`}>
      <div className="flex items-start space-x-3">
        {/* Icon */}
        <div className={`flex-shrink-0 ${style.iconColor}`}>
          {style.icon}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <h3 className={`text-sm font-medium ${style.textColor}`}>
            {style.title}
          </h3>
          <p className={`mt-1 text-sm ${style.textColor}`}>
            {error.error}
          </p>

          {/* Technical details (collapsible) */}
          {error.details && (
            <details className="mt-2">
              <summary className={`text-xs ${style.textColor} cursor-pointer hover:underline`}>
                Технические детали
              </summary>
              <pre className={`mt-1 text-xs ${style.textColor} overflow-x-auto p-2 bg-white bg-opacity-50 rounded`}>
                {error.details}
              </pre>
            </details>
          )}

          {/* Actions */}
          <div className="mt-3 flex items-center space-x-3">
            {/* Retry button */}
            {canRetry && onRetry && (
              <button
                onClick={onRetry}
                className={`
                  inline-flex items-center px-3 py-1.5 border border-transparent
                  text-xs font-medium rounded-md shadow-sm
                  ${style.iconColor} bg-white hover:bg-gray-50
                  focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500
                `}
              >
                <svg className="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clipRule="evenodd" />
                </svg>
                Повторить
              </button>
            )}

            {/* Dismiss button */}
            {onDismiss && (
              <button
                onClick={onDismiss}
                className="text-xs text-gray-500 hover:text-gray-700 underline"
              >
                Закрыть
              </button>
            )}
          </div>
        </div>

        {/* Close button */}
        {onDismiss && (
          <button
            onClick={onDismiss}
            className={`flex-shrink-0 ${style.iconColor} hover:${style.textColor}`}
          >
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
            </svg>
          </button>
        )}
      </div>
    </div>
  );
}
