/**
 * TemplateList Component
 *
 * Displays a list of ranked template results from retrieval.
 *
 * Features:
 * - Loading state with skeleton
 * - Empty state
 * - Warning messages
 * - Scrollable list of TemplateCard components
 */

import type { RetrievalResponse } from '../types/retrieval';
import { TemplateCard } from './TemplateCard';

interface TemplateListProps {
  /** Retrieval response with template results */
  response: RetrievalResponse | null;
  /** Loading state */
  isLoading?: boolean;
  /** Optional callback when template is selected */
  onTemplateSelect?: (templateId: string, answer: string) => void;
}

export function TemplateList({ response, isLoading = false, onTemplateSelect }: TemplateListProps) {
  // Loading state
  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900">
            Рекомендованные ответы
          </h3>
          <div className="animate-pulse h-4 w-16 bg-gray-200 rounded" />
        </div>

        {/* Skeleton cards */}
        {[1, 2, 3].map((i) => (
          <div key={i} className="bg-white border border-gray-200 rounded-lg p-5 animate-pulse">
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center space-x-3">
                <div className="w-8 h-8 bg-gray-200 rounded-full" />
                <div className="space-y-2">
                  <div className="h-3 w-24 bg-gray-200 rounded" />
                  <div className="h-3 w-16 bg-gray-200 rounded" />
                </div>
              </div>
              <div className="h-8 w-20 bg-gray-200 rounded" />
            </div>
            <div className="space-y-2">
              <div className="h-4 bg-gray-200 rounded w-3/4" />
              <div className="h-4 bg-gray-200 rounded w-full" />
              <div className="h-4 bg-gray-200 rounded w-5/6" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  // No results yet
  if (!response) {
    return (
      <div className="bg-gray-50 border-2 border-dashed border-gray-300 rounded-lg p-12 text-center">
        <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
        <h3 className="mt-4 text-sm font-medium text-gray-900">
          Ожидание классификации
        </h3>
        <p className="mt-2 text-sm text-gray-500">
          Введите обращение клиента и классифицируйте его для получения рекомендованных ответов
        </p>
      </div>
    );
  }

  // Empty results (no templates found)
  if (response.results.length === 0) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900">
            Рекомендованные ответы
          </h3>
          <span className="text-sm text-gray-500">
            {response.processing_time_ms.toFixed(0)}мс
          </span>
        </div>

        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-8 text-center">
          <svg className="mx-auto h-12 w-12 text-yellow-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <h3 className="mt-4 text-sm font-medium text-gray-900">
            Шаблоны не найдены
          </h3>
          <p className="mt-2 text-sm text-gray-600">
            В категории "{response.category}" → "{response.subcategory}" нет доступных шаблонов
          </p>
        </div>
      </div>
    );
  }

  // Display results
  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900">
          Рекомендованные ответы
          <span className="ml-2 text-sm font-normal text-gray-500">
            ({response.results.length} из {response.total_candidates})
          </span>
        </h3>
        <span className="text-sm text-gray-500">
          {response.processing_time_ms.toFixed(0)}мс
        </span>
      </div>

      {/* Warnings */}
      {response.warnings.length > 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <div className="flex items-start space-x-3">
            <svg className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
            <div className="flex-1">
              <h4 className="text-sm font-medium text-yellow-800">Предупреждения</h4>
              <ul className="mt-1 text-sm text-yellow-700 space-y-1">
                {response.warnings.map((warning, idx) => (
                  <li key={idx}>• {warning}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Template cards */}
      <div className="space-y-3">
        {response.results.map((template) => (
          <TemplateCard
            key={template.template_id}
            template={template}
            onSelect={
              onTemplateSelect
                ? (t) => onTemplateSelect(t.template_id, t.template_answer)
                : undefined
            }
          />
        ))}
      </div>

      {/* Footer info */}
      <div className="text-xs text-gray-500 text-center pt-2">
        Показаны наиболее релевантные шаблоны на основе вашего запроса
      </div>
    </div>
  );
}
