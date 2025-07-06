import React from 'react';
import { motion } from 'framer-motion';
import {
  DocumentTextIcon,
  CalendarIcon,
  CurrencyDollarIcon,
  MapPinIcon,
  EyeIcon,
  ArrowTopRightOnSquareIcon,
  SparklesIcon,
  InformationCircleIcon,
  CpuChipIcon,
} from '@heroicons/react/24/outline';
import { Tender } from '../services/api';

interface SearchResultsProps {
  tenders: Tender[];
  isLoading: boolean;
  error: any;
  total: number;
  offset: number;
  limit: number;
  onTenderClick: (tender: Tender) => void;
  onViewOriginal: (e: React.MouseEvent, url?: string) => void;
  queryInfo?: {
    original_query: string;
    parsed_query: string;
    filters: Record<string, any>;
    field_filters: Record<string, any>;
    wildcards: string[];
    has_errors: boolean;
    error_message?: string;
  };
  useAdvancedSearch: boolean;
  useAISearch: boolean;
}

export default function SearchResults({
  tenders,
  isLoading,
  error,
  total,
  offset,
  limit,
  onTenderClick,
  onViewOriginal,
  queryInfo,
  useAdvancedSearch,
  useAISearch
}: SearchResultsProps) {
  const formatDate = (dateString?: string) => {
    if (!dateString) return 'N/A';
    try {
      return new Date(dateString).toLocaleDateString('en-CA', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      });
    } catch {
      return 'Invalid Date';
    }
  };

  const getStatusColor = (tender: Tender) => {
    if (!tender.closing_date) return 'bg-gray-100 text-gray-800';
    const closingDate = new Date(tender.closing_date);
    const now = new Date();
    if (closingDate < now) return 'bg-red-100 text-red-800';
    if (closingDate.getTime() - now.getTime() < 7 * 24 * 60 * 60 * 1000) return 'bg-yellow-100 text-yellow-800';
    return 'bg-green-100 text-green-800';
  };

  const getStatusText = (tender: Tender) => {
    if (!tender.closing_date) return 'No Deadline';
    const closingDate = new Date(tender.closing_date);
    const now = new Date();
    if (closingDate < now) return 'Closed';
    if (closingDate.getTime() - now.getTime() < 7 * 24 * 60 * 60 * 1000) return 'Closing Soon';
    return 'Open';
  };

  const renderHighlightedText = (text: string, highlight?: string) => {
    if (!highlight || !text) return String(text || '');
    
    // Ensure both text and highlight are strings
    const textStr = String(text);
    const highlightStr = String(highlight);
    
    // Simple highlighting - in a real implementation, you'd want more sophisticated highlighting
    const parts = textStr.split(new RegExp(`(${highlightStr.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi'));
    return parts.map((part, index) => 
      part.toLowerCase() === highlightStr.toLowerCase() ? (
        <mark key={index} className="bg-yellow-200 px-1 rounded">{part}</mark>
      ) : part
    );
  };

  if (isLoading) {
    return (
      <div className="space-y-4">
        {[...Array(5)].map((_, index) => (
          <motion.div
            key={index}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
            className="card p-6 animate-pulse"
          >
            <div className="space-y-3">
              <div className="h-4 bg-gray-200 rounded w-3/4"></div>
              <div className="h-3 bg-gray-200 rounded w-1/2"></div>
              <div className="h-3 bg-gray-200 rounded w-2/3"></div>
            </div>
          </motion.div>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="card p-6 bg-red-50 border border-red-200"
      >
        <div className="text-center">
          <h3 className="text-lg font-medium text-red-800">Error Loading Results</h3>
          <p className="text-red-600 mt-2">{error.message || 'An error occurred while loading the search results.'}</p>
        </div>
      </motion.div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Search Mode Info */}
      {(useAdvancedSearch && !useAISearch) && queryInfo && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className={`card p-4 border ${
            useAISearch 
              ? 'bg-purple-50 border-purple-200' 
              : 'bg-blue-50 border-blue-200'
          }`}
        >
          <div className="flex items-start space-x-2">
            {useAISearch ? (
              <CpuChipIcon className="w-5 h-5 text-purple-600 mt-0.5" />
            ) : (
              <SparklesIcon className="w-5 h-5 text-blue-600 mt-0.5" />
            )}
            <div className="flex-1">
              <h3 className={`text-sm font-medium ${
                useAISearch ? 'text-purple-900' : 'text-blue-900'
              }`}>
                {useAISearch ? 'AI Search Results' : 'Advanced Search Results'}
              </h3>
              <div className={`mt-2 space-y-1 text-sm ${
                useAISearch ? 'text-purple-800' : 'text-blue-800'
              }`}>
                <div><strong>Original Query:</strong> {String(queryInfo.original_query || '')}</div>
                {queryInfo.parsed_query && (
                  <div><strong>Parsed Query:</strong> <code className={`px-1 rounded ${
                    useAISearch ? 'bg-purple-100' : 'bg-blue-100'
                  }`}>{String(queryInfo.parsed_query)}</code></div>
                )}
                {queryInfo.filters && Object.keys(queryInfo.filters).length > 0 && (
                  <div><strong>Filters Applied:</strong> <pre className="text-xs mt-1 p-2 bg-gray-100 rounded overflow-x-auto">{JSON.stringify(queryInfo.filters, null, 2)}</pre></div>
                )}
                {queryInfo.field_filters && Object.keys(queryInfo.field_filters).length > 0 && (
                  <div><strong>Field Filters:</strong> <pre className="text-xs mt-1 p-2 bg-gray-100 rounded overflow-x-auto">{JSON.stringify(queryInfo.field_filters, null, 2)}</pre></div>
                )}
                {queryInfo.wildcards && Array.isArray(queryInfo.wildcards) && queryInfo.wildcards.length > 0 && (
                  <div><strong>Wildcards:</strong> {queryInfo.wildcards.join(', ')}</div>
                )}
                {queryInfo.has_errors && (
                  <div className="text-red-700"><strong>Errors:</strong> {String(queryInfo.error_message || '')}</div>
                )}
              </div>
            </div>
          </div>
        </motion.div>
      )}

      {/* Results Header */}
      <div className="flex items-center justify-between">
        <div className="card p-4 flex-1">
          <h2 className="text-xl font-semibold text-gray-900">
            {total} Tenders Found
            {useAdvancedSearch && !useAISearch && (
              <span className="ml-2 inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                <SparklesIcon className="w-3 h-3 mr-1" />
                Advanced
              </span>
            )}
          </h2>
          <p className="text-sm text-gray-600 mt-1">
            Showing {offset + 1} to {Math.min(offset + limit, total)} of {total} tenders
          </p>
        </div>
      </div>

      {/* Results List */}
      {tenders.length === 0 ? (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="card p-8 text-center"
        >
          <DocumentTextIcon className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No Tenders Found</h3>
          <p className="text-gray-600">
            {useAISearch 
              ? "Try rephrasing your query or using different keywords. AI search works best with natural language descriptions."
              : "Try adjusting your search criteria or filters."
            }
          </p>
        </motion.div>
      ) : (
        <div className="space-y-4">
          {tenders.map((tender, index) => (
            <motion.div
              key={tender.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
              className="card p-6 hover:shadow-xl transition-all duration-200 cursor-pointer"
              onClick={() => onTenderClick(tender)}
            >
              <div className="space-y-4">
                {/* Header */}
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">
                      {renderHighlightedText(tender.title, String(queryInfo?.original_query || ''))}
                    </h3>
                    <div className="flex items-center space-x-4 text-sm text-gray-600">
                      <div className="flex items-center">
                        <MapPinIcon className="w-4 h-4 mr-1" />
                        {tender.organization}
                      </div>
                      <div className="flex items-center">
                        <DocumentTextIcon className="w-4 h-4 mr-1" />
                        {tender.source_name}
                      </div>
                      {tender.location && (
                        <div className="flex items-center">
                          <MapPinIcon className="w-4 h-4 mr-1" />
                          {tender.location}
                        </div>
                      )}
                    </div>
                  </div>
                  
                  {/* Status Badge */}
                  <div className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(tender)}`}>
                    {getStatusText(tender)}
                  </div>
                </div>

                {/* Description */}
                {tender.description && (
                  <p className="text-gray-700 line-clamp-2">
                    {renderHighlightedText(tender.description, String(queryInfo?.original_query || ''))}
                  </p>
                )}

                {/* Details */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                  <div className="flex items-center">
                    <CalendarIcon className="w-4 h-4 text-gray-400 mr-2" />
                    <span className="text-gray-600">Closing: {formatDate(tender.closing_date)}</span>
                  </div>
                  {tender.contract_value && (
                    <div className="flex items-center">
                      <CurrencyDollarIcon className="w-4 h-4 text-gray-400 mr-2" />
                      <span className="text-gray-600">Value: {tender.contract_value}</span>
                    </div>
                  )}
                  {tender.category && (
                    <div className="flex items-center">
                      <DocumentTextIcon className="w-4 h-4 text-gray-400 mr-2" />
                      <span className="text-gray-600">Category: {tender.category}</span>
                    </div>
                  )}
                </div>

                {/* Actions */}
                <div className="flex items-center justify-between pt-2 border-t border-gray-100">
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={(e) => onTenderClick(tender)}
                      className="flex items-center text-sm text-blue-600 hover:text-blue-800"
                    >
                      <EyeIcon className="w-4 h-4 mr-1" />
                      View Details
                    </button>
                  </div>
                  
                  {tender.url && (
                    <button
                      onClick={(e) => onViewOriginal(e, tender.url)}
                      className="flex items-center text-sm text-gray-500 hover:text-gray-700"
                    >
                      <ArrowTopRightOnSquareIcon className="w-4 h-4 mr-1" />
                      Original
                    </button>
                  )}
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
} 