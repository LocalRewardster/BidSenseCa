import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  MagnifyingGlassIcon,
  SparklesIcon,
  InformationCircleIcon,
  XMarkIcon,
  ChevronDownIcon,
  ChevronUpIcon,
  LightBulbIcon,
  CommandLineIcon,
  CpuChipIcon,
} from '@heroicons/react/24/outline';

interface AdvancedSearchProps {
  searchQuery: string;
  onSearchChange: (query: string) => void;
  onSearch: () => void;
  suggestions?: Array<{ text: string; type: string; frequency?: number }>;
  onSuggestionClick: (suggestion: string) => void;
  showSuggestions: boolean;
  setShowSuggestions: (show: boolean) => void;
  useAdvancedSearch: boolean;
  onToggleAdvancedSearch: (useAdvanced: boolean) => void;
  useAISearch: boolean;
  onToggleAISearch: (useAI: boolean) => void;
  searchExamples?: Array<{ query: string; description: string }>;
}

export default function AdvancedSearch({
  searchQuery,
  onSearchChange,
  onSearch,
  suggestions,
  onSuggestionClick,
  showSuggestions,
  setShowSuggestions,
  useAdvancedSearch,
  onToggleAdvancedSearch,
  useAISearch,
  onToggleAISearch,
  searchExamples = []
}: AdvancedSearchProps) {
  const [showAdvancedPanel, setShowAdvancedPanel] = useState(false);
  const [showExamples, setShowExamples] = useState(false);
  const searchRef = useRef<HTMLDivElement>(null);

  // Handle click outside to close suggestions
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(event.target as Node)) {
        setShowSuggestions(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [setShowSuggestions]);

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      onSearch();
      setShowSuggestions(false);
    }
  };

  const handleExampleClick = (example: string) => {
    onSearchChange(example);
    setShowExamples(false);
    onSearch();
  };

  const defaultExamples = [
    { query: 'Show me bridge maintenance tenders in BC closing this month over $500K', description: 'Natural language query for specific requirements' },
    { query: 'IT services in Ontario under $100K', description: 'Find IT services with budget constraints' },
    { query: 'construction projects in Alberta and Saskatchewan', description: 'Multi-province construction search' },
    { query: 'healthcare equipment in Quebec closing next week', description: 'Time-sensitive healthcare search' },
    { query: 'software development services for government', description: 'Broad category search with context' },
    { query: 'environmental consulting in western provinces', description: 'Regional service search' }
  ];

  const aiExamples = [
    { query: 'Show me bridge maintenance tenders in BC closing this month over $500K', description: 'Natural language query for specific requirements' },
    { query: 'IT services in Ontario under $100K', description: 'Find IT services with budget constraints' },
    { query: 'construction projects in Alberta and Saskatchewan', description: 'Multi-province construction search' },
    { query: 'healthcare equipment in Quebec closing next week', description: 'Time-sensitive healthcare search' },
    { query: 'software development services for government', description: 'Broad category search with context' },
    { query: 'environmental consulting in western provinces', description: 'Regional service search' }
  ];

  const examples = searchExamples.length > 0 ? searchExamples : defaultExamples;

  return (
    <div className="space-y-6">
      {/* Help and Examples Buttons */}
      <div className="flex items-center justify-end space-x-3">
        <button
          onClick={() => setShowAdvancedPanel(!showAdvancedPanel)}
          className="flex items-center space-x-2 px-3 py-2 text-sm text-gray-500 hover:text-gray-700 hover:bg-gray-50 rounded-lg transition-colors duration-200"
        >
          {showAdvancedPanel ? (
            <ChevronUpIcon className="w-4 h-4" />
          ) : (
            <ChevronDownIcon className="w-4 h-4" />
          )}
          <span>Help</span>
        </button>

        <button
          onClick={() => setShowExamples(!showExamples)}
          className="flex items-center space-x-2 px-3 py-2 text-sm text-gray-500 hover:text-gray-700 hover:bg-gray-50 rounded-lg transition-colors duration-200"
        >
          <LightBulbIcon className="w-4 h-4" />
          <span>Examples</span>
        </button>
      </div>

      {/* Search Mode Help Panel */}
      <AnimatePresence>
        {showAdvancedPanel && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="card p-6 border bg-purple-50 border-purple-200"
          >
            <div className="space-y-4">
              <div className="flex items-start space-x-3">
                <InformationCircleIcon className="w-6 h-6 mt-0.5 text-purple-600" />
                <div className="flex-1">
                  <h3 className="text-base font-medium text-purple-900">
                    AI Search Features
                  </h3>
                  <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-purple-800">
                    <div>
                      <strong>Natural Language:</strong>
                      <ul className="mt-1 space-y-1">
                        <li>• Ask questions in plain English</li>
                        <li>• Specify provinces, values, deadlines</li>
                        <li>• Use natural language filters</li>
                      </ul>
                    </div>
                    <div>
                      <strong>Smart Understanding:</strong>
                      <ul className="mt-1 space-y-1">
                        <li>• Understands context and intent</li>
                        <li>• Combines multiple search criteria</li>
                        <li>• Provides relevant results</li>
                      </ul>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Search Examples Panel */}
      <AnimatePresence>
        {showExamples && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="card p-6 border bg-amber-50 border-amber-200"
          >
            <div className="space-y-4">
              <div className="flex items-start space-x-3">
                <LightBulbIcon className="w-6 h-6 text-amber-600 mt-0.5" />
                <div className="flex-1">
                  <h3 className="text-base font-medium text-amber-900">
                    AI Search Examples
                  </h3>
                  <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-4">
                    {examples.map((example, index) => (
                      <button
                        key={index}
                        onClick={() => handleExampleClick(example.query)}
                        className="text-left p-3 rounded-lg hover:bg-amber-100 transition-colors duration-200"
                      >
                        <div className="text-sm font-medium text-amber-800">
                          <CommandLineIcon className="w-4 h-4 inline mr-2" />
                          {example.query}
                        </div>
                        <div className="text-xs text-amber-700 mt-2">
                          {example.description}
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Search Input */}
      <div className="relative" ref={searchRef}>
        <div className="relative">
          <MagnifyingGlassIcon className="absolute left-4 top-1/2 transform -translate-y-1/2 w-6 h-6 text-gray-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            onKeyPress={handleKeyPress}
            onFocus={() => setShowSuggestions(true)}
            placeholder="Try: 'construction projects in Ontario' or 'IT services under $50k'"
            className="w-full pl-12 pr-12 py-4 text-lg border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900 placeholder-gray-500 shadow-sm hover:shadow-md transition-shadow duration-200"
          />
          
          {searchQuery && (
            <button
              onClick={() => {
                onSearchChange('');
                setShowSuggestions(false);
              }}
              className="absolute right-4 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600 transition-colors duration-200"
            >
              <XMarkIcon className="w-5 h-5" />
            </button>
          )}
        </div>
        
        {/* Search Suggestions */}
        <AnimatePresence>
          {showSuggestions && suggestions && suggestions.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="absolute z-10 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-60 overflow-y-auto"
            >
              {suggestions.map((suggestion, index) => (
                <button
                  key={index}
                  onClick={() => onSuggestionClick(suggestion.text)}
                  className="w-full px-4 py-3 text-left hover:bg-gray-50 flex items-center justify-between border-b border-gray-100 last:border-b-0"
                >
                  <div className="flex items-center">
                    <MagnifyingGlassIcon className="w-4 h-4 text-gray-400 mr-2" />
                    <span className="text-sm font-medium">{suggestion.text}</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className="text-xs text-gray-500 capitalize bg-gray-100 px-2 py-1 rounded">
                      {suggestion.type}
                    </span>
                    {suggestion.frequency && (
                      <span className="text-xs text-gray-400">
                        {suggestion.frequency}
                      </span>
                    )}
                  </div>
                </button>
              ))}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
} 