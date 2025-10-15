/**
 * ClassificationDisplay Component
 *
 * Displays classification results with category, subcategory, and confidence.
 *
 * Features:
 * - Visual confidence indicator (color-coded)
 * - Processing time display
 * - Expandable inquiry text
 * - Clean, professional design
 */

import type { ClassificationResult } from '../types/classification';

interface ClassificationDisplayProps {
  /** Classification result to display */
  result: ClassificationResult;
}

export function ClassificationDisplay({ result }: ClassificationDisplayProps) {
  // Determine confidence level and color
  const getConfidenceLevel = (confidence: number): { label: string; color: string; bgColor: string } => {
    if (confidence >= 0.8) {
      return { label: 'Высокая', color: 'text-green-700', bgColor: 'bg-green-100' };
    } else if (confidence >= 0.5) {
      return { label: 'Средняя', color: 'text-yellow-700', bgColor: 'bg-yellow-100' };
    } else {
      return { label: 'Низкая', color: 'text-red-700', bgColor: 'bg-red-100' };
    }
  };

  const confidenceInfo = getConfidenceLevel(result.confidence);
  const confidencePercent = Math.round(result.confidence * 100);

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900">
          Результат классификации
        </h3>
        <span className="text-sm text-gray-500">
          {result.processing_time_ms}мс
        </span>
      </div>

      {/* Inquiry (truncated) */}
      <div className="bg-gray-50 rounded-md p-3">
        <p className="text-sm text-gray-600 line-clamp-2">
          {result.inquiry}
        </p>
      </div>

      {/* Classification results */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Category */}
        <div>
          <label className="block text-xs font-medium text-gray-500 uppercase mb-1">
            Категория
          </label>
          <div className="bg-blue-50 border border-blue-200 rounded-md px-3 py-2">
            <p className="text-sm font-medium text-blue-900">
              {result.category}
            </p>
          </div>
        </div>

        {/* Subcategory */}
        <div>
          <label className="block text-xs font-medium text-gray-500 uppercase mb-1">
            Подкатегория
          </label>
          <div className="bg-blue-50 border border-blue-200 rounded-md px-3 py-2">
            <p className="text-sm font-medium text-blue-900">
              {result.subcategory}
            </p>
          </div>
        </div>
      </div>

      {/* Confidence indicator */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <label className="block text-xs font-medium text-gray-500 uppercase">
            Уверенность классификации
          </label>
          <span className={`text-sm font-semibold ${confidenceInfo.color}`}>
            {confidenceInfo.label} ({confidencePercent}%)
          </span>
        </div>

        {/* Progress bar */}
        <div className="w-full bg-gray-200 rounded-full h-2.5">
          <div
            className={`h-2.5 rounded-full transition-all duration-500 ${
              result.confidence >= 0.8
                ? 'bg-green-600'
                : result.confidence >= 0.5
                ? 'bg-yellow-500'
                : 'bg-red-500'
            }`}
            style={{ width: `${confidencePercent}%` }}
          />
        </div>

        {/* Confidence badge */}
        <div className="mt-2 flex items-center space-x-2">
          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${confidenceInfo.bgColor} ${confidenceInfo.color}`}>
            {confidencePercent}% уверенность
          </span>
          {result.confidence < 0.5 && (
            <span className="text-xs text-gray-500">
              ⚠️ Рекомендуется проверка оператором
            </span>
          )}
        </div>
      </div>

      {/* Status indicator */}
      <div className="pt-4 border-t border-gray-200">
        <div className="flex items-center space-x-2 text-sm text-green-600">
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
          </svg>
          <span className="font-medium">Классификация выполнена успешно</span>
        </div>
      </div>
    </div>
  );
}
