/**
 * Smart Support Operator Interface - Main App
 *
 * Complete operator workflow:
 * 1. Operator submits customer inquiry
 * 2. System classifies inquiry → category + subcategory
 * 3. System retrieves top 5 relevant templates
 * 4. Operator can copy template answer to clipboard
 *
 * Performance requirements:
 * - Classification: <2s (FR-005)
 * - Retrieval: <1s (FR-010)
 * - Total workflow: <10s (FR-015)
 */

import { useState } from 'react';
import { InquiryInput } from './components/InquiryInput';
import { ClassificationDisplay } from './components/ClassificationDisplay';
import { TemplateList } from './components/TemplateList';
import { ErrorDisplay } from './components/ErrorDisplay';
import { useClassify } from './hooks/useClassify';
import { useRetrieve } from './hooks/useRetrieve';
import { useHealth } from './hooks/useHealth';
import type { ClassificationResult, ErrorResponse } from './types/classification';
import type { RetrievalResponse } from './types/retrieval';

function App() {
  // State
  const [classificationResult, setClassificationResult] = useState<ClassificationResult | null>(null);
  const [retrievalResponse, setRetrievalResponse] = useState<RetrievalResponse | null>(null);
  const [currentError, setCurrentError] = useState<ErrorResponse | null>(null);

  // React Query hooks
  const classifyMutation = useClassify();
  const retrieveMutation = useRetrieve();
  const { data: healthData } = useHealth({ refetchInterval: 30000 }); // Poll every 30s

  // Handle inquiry submission
  const handleInquirySubmit = async (inquiry: string) => {
    // Reset previous results and errors
    setClassificationResult(null);
    setRetrievalResponse(null);
    setCurrentError(null);

    try {
      // Step 1: Classify inquiry
      const classificationData = await classifyMutation.mutateAsync(inquiry);
      setClassificationResult(classificationData);

      // Step 2: Retrieve templates
      const retrievalData = await retrieveMutation.mutateAsync({
        query: inquiry,
        category: classificationData.category,
        subcategory: classificationData.subcategory,
        classification_confidence: classificationData.confidence,
        top_k: 5,
      });
      setRetrievalResponse(retrievalData);
    } catch (error) {
      // Error is already transformed by Axios interceptor to ErrorResponse
      setCurrentError(error as ErrorResponse);
    }
  };

  // Handle retry
  const handleRetry = () => {
    setCurrentError(null);
    // Trigger re-submission if there was a classification result
    if (classificationResult) {
      handleInquirySubmit(classificationResult.inquiry);
    }
  };

  // Determine loading states
  const isClassifying = classifyMutation.isPending;
  const isRetrieving = retrieveMutation.isPending;
  const isProcessing = isClassifying || isRetrieving;

  // Check health status
  const isHealthy = healthData?.status === 'healthy';
  const isRetrievalAvailable = healthData?.retrieval_available ?? false;

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">
                Smart Support
              </h1>
              <p className="mt-1 text-sm text-gray-600">
                Интеллектуальная система поддержки операторов
              </p>
            </div>

            {/* Health indicator */}
            {healthData && (
              <div className="flex items-center space-x-2">
                <div className={`w-3 h-3 rounded-full ${isHealthy ? 'bg-green-500' : 'bg-yellow-500'}`} />
                <span className="text-sm text-gray-600">
                  {isHealthy ? 'Система работает' : 'Ограниченная функциональность'}
                </span>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Left column: Input and Classification */}
          <div className="space-y-6">
            {/* Service status warning */}
            {healthData && !isRetrievalAvailable && (
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                <div className="flex items-start space-x-3">
                  <svg className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                  </svg>
                  <div className="text-sm text-yellow-800">
                    <p className="font-medium">Сервис поиска шаблонов недоступен</p>
                    <p className="mt-1">Классификация работает, но поиск шаблонов временно недоступен. Загружено шаблонов: {healthData.embeddings_count}</p>
                  </div>
                </div>
              </div>
            )}

            {/* Inquiry input */}
            <div className="bg-white rounded-lg shadow-md p-6">
              <InquiryInput
                onSubmit={handleInquirySubmit}
                isLoading={isProcessing}
                disabled={isProcessing}
              />
            </div>

            {/* Classification result */}
            {classificationResult && !isClassifying && (
              <ClassificationDisplay result={classificationResult} />
            )}

            {/* Loading indicator for classification */}
            {isClassifying && (
              <div className="bg-white border border-gray-200 rounded-lg p-12 text-center">
                <svg className="animate-spin h-12 w-12 text-blue-600 mx-auto" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                <p className="mt-4 text-sm text-gray-600">Классификация обращения...</p>
              </div>
            )}

            {/* Error display */}
            {currentError && (
              <ErrorDisplay
                error={currentError}
                onRetry={handleRetry}
                onDismiss={() => setCurrentError(null)}
              />
            )}
          </div>

          {/* Right column: Template results */}
          <div className="space-y-6">
            <div className="bg-white rounded-lg shadow-md p-6">
              <TemplateList
                response={retrievalResponse}
                isLoading={isRetrieving}
              />
            </div>
          </div>
        </div>

        {/* Performance metrics (development only) */}
        {import.meta.env.DEV && (classificationResult || retrievalResponse) && (
          <div className="mt-8 bg-gray-800 text-white rounded-lg p-4 text-xs font-mono">
            <div className="font-bold mb-2">Performance Metrics:</div>
            <div className="grid grid-cols-3 gap-4">
              {classificationResult && (
                <div>
                  <div className="text-gray-400">Classification:</div>
                  <div className={classificationResult.processing_time_ms < 2000 ? 'text-green-400' : 'text-red-400'}>
                    {classificationResult.processing_time_ms}ms
                    {classificationResult.processing_time_ms < 2000 ? ' ✓' : ' ✗ (>2s)'}
                  </div>
                </div>
              )}
              {retrievalResponse && (
                <div>
                  <div className="text-gray-400">Retrieval:</div>
                  <div className={retrievalResponse.processing_time_ms < 1000 ? 'text-green-400' : 'text-red-400'}>
                    {retrievalResponse.processing_time_ms.toFixed(0)}ms
                    {retrievalResponse.processing_time_ms < 1000 ? ' ✓' : ' ✗ (>1s)'}
                  </div>
                </div>
              )}
              {classificationResult && retrievalResponse && (
                <div>
                  <div className="text-gray-400">Total:</div>
                  <div className={
                    (classificationResult.processing_time_ms + retrievalResponse.processing_time_ms) < 10000
                      ? 'text-green-400'
                      : 'text-red-400'
                  }>
                    {(classificationResult.processing_time_ms + retrievalResponse.processing_time_ms).toFixed(0)}ms
                    {(classificationResult.processing_time_ms + retrievalResponse.processing_time_ms) < 10000 ? ' ✓' : ' ✗ (>10s)'}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="mt-12 bg-white border-t border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <p className="text-center text-sm text-gray-500">
            Smart Support © 2025 | Minsk Hackathon | Powered by Scibox AI
          </p>
        </div>
      </footer>
    </div>
  );
}

export default App;
