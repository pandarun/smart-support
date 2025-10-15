/**
 * TemplateCard Component
 *
 * Displays a single template result with question, answer, and relevance score.
 *
 * Features:
 * - Copy-to-clipboard functionality for answer
 * - Expandable/collapsible answer text
 * - Visual relevance indicator
 * - Rank badge
 */

import { useState } from 'react';
import type { TemplateResult } from '../types/retrieval';

interface TemplateCardProps {
  /** Template result to display */
  template: TemplateResult;
  /** Optional click handler for template selection */
  onSelect?: (template: TemplateResult) => void;
}

export function TemplateCard({ template, onSelect }: TemplateCardProps) {
  const [copied, setCopied] = useState(false);
  const [expanded, setExpanded] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(template.template_answer);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy text:', err);
    }
  };

  const handleClick = () => {
    if (onSelect) {
      onSelect(template);
    }
  };

  // Determine relevance level
  const getRelevanceInfo = (score: number) => {
    if (score >= 0.8) {
      return { label: 'Высокая', color: 'text-green-700', bgColor: 'bg-green-100', borderColor: 'border-green-300' };
    } else if (score >= 0.5) {
      return { label: 'Средняя', color: 'text-yellow-700', bgColor: 'bg-yellow-100', borderColor: 'border-yellow-300' };
    } else {
      return { label: 'Низкая', color: 'text-gray-700', bgColor: 'bg-gray-100', borderColor: 'border-gray-300' };
    }
  };

  const relevanceInfo = getRelevanceInfo(template.similarity_score);
  const scorePercent = Math.round(template.similarity_score * 100);

  // Truncate answer for collapsed view
  const shouldTruncate = template.template_answer.length > 200;
  const displayAnswer = expanded || !shouldTruncate
    ? template.template_answer
    : template.template_answer.substring(0, 200) + '...';

  return (
    <div
      className={`
        bg-white border-2 rounded-lg p-5
        transition-all duration-200
        hover:shadow-md
        ${relevanceInfo.borderColor}
        ${onSelect ? 'cursor-pointer' : ''}
      `}
      onClick={handleClick}
    >
      {/* Header with rank and score */}
      <div className="flex items-start justify-between mb-3">
        {/* Rank badge */}
        <div className="flex items-center space-x-3">
          <div className="flex-shrink-0 w-8 h-8 bg-blue-600 text-white rounded-full flex items-center justify-center font-bold text-sm">
            {template.rank}
          </div>
          <div>
            <div className={`text-xs font-medium ${relevanceInfo.color}`}>
              {relevanceInfo.label} релевантность
            </div>
            <div className="text-xs text-gray-500">
              Оценка: {scorePercent}%
            </div>
          </div>
        </div>

        {/* Copy button */}
        <button
          onClick={(e) => {
            e.stopPropagation();
            handleCopy();
          }}
          className={`
            px-3 py-1.5 rounded-md text-xs font-medium
            transition-colors duration-200
            ${
              copied
                ? 'bg-green-100 text-green-700'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }
          `}
        >
          {copied ? (
            <span className="flex items-center space-x-1">
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
              </svg>
              <span>Скопировано</span>
            </span>
          ) : (
            <span className="flex items-center space-x-1">
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path d="M8 3a1 1 0 011-1h2a1 1 0 110 2H9a1 1 0 01-1-1z" />
                <path d="M6 3a2 2 0 00-2 2v11a2 2 0 002 2h8a2 2 0 002-2V5a2 2 0 00-2-2 3 3 0 01-3 3H9a3 3 0 01-3-3z" />
              </svg>
              <span>Копировать</span>
            </span>
          )}
        </button>
      </div>

      {/* Question */}
      <div className="mb-3">
        <h4 className="text-sm font-semibold text-gray-900 mb-1">
          Вопрос:
        </h4>
        <p className="text-sm text-gray-700">
          {template.template_question}
        </p>
      </div>

      {/* Answer */}
      <div>
        <h4 className="text-sm font-semibold text-gray-900 mb-1">
          Ответ:
        </h4>
        <p className="text-sm text-gray-700 whitespace-pre-wrap">
          {displayAnswer}
        </p>

        {/* Expand/collapse button */}
        {shouldTruncate && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              setExpanded(!expanded);
            }}
            className="mt-2 text-xs text-blue-600 hover:text-blue-700 font-medium"
          >
            {expanded ? 'Свернуть' : 'Показать полностью'}
          </button>
        )}
      </div>

      {/* Footer metadata */}
      <div className="mt-4 pt-3 border-t border-gray-200 flex items-center justify-between text-xs text-gray-500">
        <span>ID: {template.template_id}</span>
        <span>{template.category} → {template.subcategory}</span>
      </div>
    </div>
  );
}
