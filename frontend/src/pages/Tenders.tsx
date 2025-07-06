import React, { useState, useMemo, useRef, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  MagnifyingGlassIcon,
  FunnelIcon,
  DocumentTextIcon,
  CalendarIcon,
  CurrencyDollarIcon,
  MapPinIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  ExclamationTriangleIcon,
  EyeIcon,
  XMarkIcon,
  SparklesIcon,
} from '@heroicons/react/24/outline';
import { apiService, Tender, TenderFilters, SearchExample } from '../services/api';
import AdvancedSearch from '../components/AdvancedSearch';
import SearchResults from '../components/SearchResults';

export default function Tenders() {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedSource, setSelectedSource] = useState('all');
  const [selectedProvince, setSelectedProvince] = useState('all');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [currentPage, setCurrentPage] = useState(1);
  const [sortBy, setSortBy] = useState('created_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [useAdvancedSearch, setUseAdvancedSearch] = useState(false);
  const [useAISearch, setUseAISearch] = useState(true);
  const searchRef = useRef<HTMLDivElement>(null);
  const itemsPerPage = 20;

  // Calculate offset for pagination
  const offset = (currentPage - 1) * itemsPerPage;

  // Fetch filters
  const { data: filters, isLoading: filtersLoading } = useQuery<TenderFilters>({
    queryKey: ['tender-filters'],
    queryFn: () => apiService.getTenderFilters(),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  // Fetch search suggestions
  const { data: suggestions } = useQuery({
    queryKey: ['search-suggestions', searchQuery],
    queryFn: () => apiService.getSearchSuggestions(searchQuery, 5),
    enabled: searchQuery.length >= 2,
    staleTime: 1 * 60 * 1000, // 1 minute
  });

  // Fetch search examples
  const { data: searchExamples } = useQuery<{ success: boolean; data: SearchExample[]; error?: string }>({
    queryKey: ['search-examples'],
    queryFn: () => apiService.getSearchExamples(),
    staleTime: 10 * 60 * 1000, // 10 minutes
  });

  // Fetch tenders from API with filters
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['tenders', searchQuery, selectedSource, selectedProvince, selectedCategory, offset, sortBy, sortOrder, useAdvancedSearch, useAISearch],
    queryFn: () => {
      if (useAISearch) {
        // Use AI search endpoint
        return apiService.searchWithAI(searchQuery, {
          limit: itemsPerPage,
          offset,
          source: selectedSource !== 'all' ? selectedSource : undefined,
          province: selectedProvince !== 'all' ? selectedProvince : undefined,
          category: selectedCategory !== 'all' ? selectedCategory : undefined,
          sort_by: sortBy,
          sort_order: sortOrder,
        });
      } else {
        // Use regular search
        return apiService.getTenders({
          limit: itemsPerPage,
          offset,
          search: searchQuery || undefined,
          source: selectedSource !== 'all' ? selectedSource : undefined,
          province: selectedProvince !== 'all' ? selectedProvince : undefined,
          category: selectedCategory !== 'all' ? selectedCategory : undefined,
          sort_by: sortBy,
          sort_order: sortOrder,
          use_advanced_search: useAdvancedSearch,
        });
      }
    },
    keepPreviousData: true,
  });

  // Handle click outside search suggestions
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(event.target as Node)) {
        setShowSuggestions(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

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

  const totalPages = data ? Math.ceil(data.total / itemsPerPage) : 0;

  const handleSearch = () => {
    setCurrentPage(1); // Reset to first page when searching
    setShowSuggestions(false);
    refetch();
  };

  const handleSuggestionClick = (suggestion: string) => {
    setSearchQuery(suggestion);
    setShowSuggestions(false);
    setCurrentPage(1);
    refetch();
  };

  const handleClearFilters = () => {
    setSearchQuery('');
    setSelectedSource('all');
    setSelectedProvince('all');
    setSelectedCategory('all');
    setCurrentPage(1);
    setSortBy('created_at');
    setSortOrder('desc');
    setUseAdvancedSearch(false);
    setUseAISearch(true);
  };

  const handleTenderClick = (tender: Tender) => {
    navigate(`/tenders/${tender.id}`);
  };

  const handleViewOriginal = (e: React.MouseEvent, url?: string) => {
    e.stopPropagation();
    if (url) {
      window.open(url, '_blank');
    }
  };

  const activeFiltersCount = [
    searchQuery,
    selectedSource !== 'all',
    selectedProvince !== 'all',
    selectedCategory !== 'all',
    sortBy !== 'created_at',
    sortOrder !== 'desc',
    useAdvancedSearch,
    useAISearch
  ].filter(Boolean).length;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="p-6 space-y-6"
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Tenders</h1>
          <p className="text-gray-600 mt-1">Manage and track government tenders</p>
        </div>
        <div className="flex space-x-2">
          <button
            onClick={() => refetch()}
            className="btn-secondary"
          >
            <DocumentTextIcon className="w-5 h-5 mr-2" />
            Refresh
          </button>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="card p-4 bg-red-50 border border-red-200"
        >
          <div className="flex items-center">
            <ExclamationTriangleIcon className="w-5 h-5 text-red-600 mr-2" />
            <div>
              <h3 className="text-sm font-medium text-red-800">Connection Error</h3>
              <p className="text-sm text-red-700 mt-1">
                Unable to connect to the backend API. Please ensure the backend server is running.
              </p>
            </div>
          </div>
        </motion.div>
      )}

      {/* Advanced Search Component */}
      <div className="card p-6">
        <AdvancedSearch
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          onSearch={handleSearch}
          suggestions={suggestions?.success ? suggestions.data : undefined}
          onSuggestionClick={handleSuggestionClick}
          showSuggestions={showSuggestions}
          setShowSuggestions={setShowSuggestions}
          useAdvancedSearch={useAdvancedSearch}
          onToggleAdvancedSearch={setUseAdvancedSearch}
          useAISearch={useAISearch}
          onToggleAISearch={setUseAISearch}
          searchExamples={searchExamples?.success ? searchExamples.data : undefined}
        />

        {/* Additional Filters */}
        <div className="mt-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Source Filter */}
          <select
            value={selectedSource}
            onChange={(e) => setSelectedSource(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            disabled={filtersLoading}
          >
            <option value="all">All Sources</option>
            {filtersLoading ? (
              <option disabled>Loading...</option>
            ) : (
              filters?.sources?.map(source => (
                <option key={source} value={source}>{source}</option>
              ))
            )}
          </select>

          {/* Province Filter */}
          <select
            value={selectedProvince}
            onChange={(e) => setSelectedProvince(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            disabled={filtersLoading}
          >
            <option value="all">All Provinces</option>
            {filtersLoading ? (
              <option disabled>Loading...</option>
            ) : (
              filters?.provinces?.map(province => (
                <option key={province} value={province}>{province}</option>
              ))
            )}
          </select>

          {/* Category Filter */}
          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            disabled={filtersLoading}
          >
            <option value="all">All Categories</option>
            {filtersLoading ? (
              <option disabled>Loading...</option>
            ) : (
              filters?.categories?.map(category => (
                <option key={category} value={category}>{category}</option>
              ))
            )}
          </select>

          {/* Sort By */}
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="created_at">Date Added</option>
            <option value="title">Title</option>
            <option value="organization">Organization</option>
            <option value="closing_date">Closing Date</option>
            {(useAdvancedSearch || useAISearch) && <option value="rank">Relevance</option>}
          </select>
        </div>

        {/* Sort Order */}
        <div className="mt-4 flex items-center space-x-4">
          <select
            value={sortOrder}
            onChange={(e) => setSortOrder(e.target.value as 'asc' | 'desc')}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="desc">Descending</option>
            <option value="asc">Ascending</option>
          </select>

          {/* Filter Actions */}
          <div className="flex items-center space-x-2">
            {activeFiltersCount > 0 && (
              <button
                onClick={handleClearFilters}
                className="btn-secondary"
              >
                <XMarkIcon className="w-4 h-4 mr-2" />
                Clear All ({activeFiltersCount})
              </button>
            )}
          </div>
        </div>

        {/* Active Filters Display */}
        {data?.filters_applied && Object.keys(data.filters_applied).length > 0 && !useAISearch && (
          <div className="mt-4 pt-4 border-t border-gray-200">
            <div className="flex items-center space-x-2 text-sm text-gray-600">
              <span>Active filters:</span>
              {Object.entries(data.filters_applied).map(([key, value]) => (
                <span key={key} className="px-2 py-1 bg-blue-100 text-blue-800 rounded-full text-xs">
                  {key}: {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Search Results */}
      <SearchResults
        tenders={data?.tenders || []}
        isLoading={isLoading}
        error={error}
        total={data?.total || 0}
        offset={offset}
        limit={itemsPerPage}
        onTenderClick={handleTenderClick}
        onViewOriginal={handleViewOriginal}
        queryInfo={data?.query_info}
        useAdvancedSearch={useAdvancedSearch}
        useAISearch={useAISearch}
      />

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <div className="text-sm text-gray-700">
            Page {currentPage} of {totalPages}
          </div>
          <div className="flex space-x-2">
            <button
              onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
              disabled={currentPage === 1}
              className="px-3 py-2 border border-gray-300 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
            >
              <ChevronLeftIcon className="w-4 h-4" />
            </button>
            <button
              onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
              disabled={currentPage === totalPages}
              className="px-3 py-2 border border-gray-300 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
            >
              <ChevronRightIcon className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </motion.div>
  );
} 