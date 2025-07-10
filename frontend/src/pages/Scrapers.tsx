import React, { useState, useEffect, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import {
  PlayIcon,
  StopIcon,
  ClockIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  CogIcon,
  DocumentTextIcon,
  ArrowPathIcon,
  GlobeAltIcon,
  MapPinIcon,
  InformationCircleIcon,
  SparklesIcon,
  TableCellsIcon,
} from '@heroicons/react/24/outline';
import { apiService } from '../services/api';
import toast from 'react-hot-toast';

interface ScraperStatus {
  name: string;
  status: 'idle' | 'running' | 'completed' | 'failed';
  last_run?: string;
  next_run?: string;
  total_tenders: number;
  recent_tenders: number;
  error_message?: string;
}

interface ScraperLog {
  timestamp: string;
  level: 'INFO' | 'WARNING' | 'ERROR';
  message: string;
  scraper?: string;
}

interface EnrichmentStatus {
  status: string;
  last_run: string | null;
  last_result: any;
  error: string | null;
  incomplete_tenders: number;
}

export default function Scrapers() {
  const queryClient = useQueryClient();
  const [selectedScraper, setSelectedScraper] = useState<string | null>(null);
  const [enrichmentLimit, setEnrichmentLimit] = useState(4);
  const [isRefreshingTenders, setIsRefreshingTenders] = useState(false);

  // Track previous scraper status to detect changes
  const previousScraperStatus = useRef<Record<string, string>>({});

  // Fetch scraper status from API
  const { data: scraperStatus, isLoading: statusLoading, error: statusError } = useQuery({
    queryKey: ['scraper-status'],
    queryFn: () => apiService.getScraperStatus(),
    refetchInterval: (data) => {
      // Use shorter interval if any scraper is running
      if (data?.data) {
        const isAnyRunning = Object.values(data.data).some((scraper: any) => scraper.status === 'running');
        return isAnyRunning ? 5000 : 30000; // 5 seconds when running, 30 seconds when idle
      }
      return 30000; // Default to 30 seconds
    },
  });

  // Convert API data to the expected format and filter for CanadaBuys only
  const scrapers = scraperStatus?.data ? Object.entries(scraperStatus.data)
    .filter(([id]) => id === 'canadabuys')
    .map(([id, data]: [string, any]) => ({
      id,
      name: data.name || 'CanadaBuys',
      status: data.status,
      last_run: data.last_run,
      next_run: data.next_run,
      total_tenders: data.total_tenders || 0,
      recent_tenders: data.recent_tenders || 0,
      error_message: data.error_message,
    })) : [];

  // Fetch enrichment status from API
  const { data: enrichmentStatus, isLoading: enrichmentLoading, error: enrichmentError } = useQuery({
    queryKey: ['enrichment-status'],
    queryFn: () => apiService.getEnrichmentStatus(),
    refetchInterval: 10000, // Refetch every 10 seconds
  });

  // Fetch incomplete tenders for preview
  const { data: incompleteTenders, isLoading: incompleteTendersLoading } = useQuery({
    queryKey: ['incomplete-tenders'],
    queryFn: () => apiService.getIncompleteTenders(3), // Get 3 for preview
    refetchInterval: 30000, // Refetch every 30 seconds
  });

  // Fetch scraper logs from API
  const { data: scraperLogs, isLoading: logsLoading, error: logsError } = useQuery({
    queryKey: ['scraper-logs', selectedScraper],
    queryFn: () => apiService.getScraperLogs(selectedScraper),
    refetchInterval: 30000, // Refetch every 30 seconds
  });

  // Detect scraper completion and refresh tenders
  useEffect(() => {
    if (scraperStatus?.data) {
      const currentStatuses: Record<string, string> = {};
      
      // Check each scraper's status
      Object.entries(scraperStatus.data).forEach(([scraperId, data]: [string, any]) => {
        const currentStatus = data.status;
        const previousStatus = previousScraperStatus.current[scraperId];
        
        currentStatuses[scraperId] = currentStatus;
        
        // If scraper changed from 'running' to 'completed', refresh tenders
        if (previousStatus === 'running' && currentStatus === 'completed') {
          console.log(`Scraper ${scraperId} completed, refreshing tenders...`);
          
          // Set refreshing state
          setIsRefreshingTenders(true);
          
          // Invalidate all tender-related queries to refresh the data
          Promise.all([
            queryClient.invalidateQueries({ queryKey: ['tenders'] }),
            queryClient.invalidateQueries({ queryKey: ['tender-stats'] }),
            queryClient.invalidateQueries({ queryKey: ['recent-tenders'] }),
            queryClient.invalidateQueries({ queryKey: ['tender-filters'] }),
            queryClient.invalidateQueries({ queryKey: ['search-suggestions'] }),
            queryClient.invalidateQueries({ queryKey: ['search-examples'] }),
          ]).then(() => {
            // Clear refreshing state after all queries are invalidated
            setIsRefreshingTenders(false);
          });
          
          // Show success notification with tender count
          const recentTenders = data.recent_tenders || 0;
          const totalTenders = data.total_tenders || 0;
          toast.success(
            `${data.name || scraperId} scraper completed! ${recentTenders} new tenders added. Total: ${totalTenders}`,
            { duration: 6000 }
          );
        }
        
        // If scraper changed from 'running' to 'failed', show error
        if (previousStatus === 'running' && currentStatus === 'failed') {
          console.log(`Scraper ${scraperId} failed`);
          toast.error(
            `${data.name || scraperId} scraper failed: ${data.error_message || 'Unknown error'}`,
            { duration: 8000 }
          );
        }
      });
      
      // Update previous status for next comparison
      previousScraperStatus.current = currentStatuses;
    }
  }, [scraperStatus, queryClient]);

  // Trigger scraper mutation
  const triggerScraperMutation = useMutation({
    mutationFn: async (scraperName: string) => {
      return apiService.triggerScraper(scraperName);
    },
    onSuccess: (data, scraperName) => {
      toast.success(`${scraperName} scraper triggered successfully`);
      queryClient.invalidateQueries({ queryKey: ['scraper-status'] });
      queryClient.invalidateQueries({ queryKey: ['scraper-logs'] });
    },
    onError: (error) => {
      toast.error('Failed to trigger scraper');
    },
  });

  // Trigger enrichment mutation
  const triggerEnrichmentMutation = useMutation({
    mutationFn: async (limit: number) => {
      return apiService.processEnrichment(limit);
    },
    onSuccess: (data) => {
      // Show detailed success message based on the response
      if (data.tasks_created && data.tasks_created > 0) {
        toast.success(
          `Enrichment completed! ${data.tasks_created} tasks created in Airtable for VAs to process.`,
          { duration: 6000 }
        );
      } else if (data.processed === 0) {
        toast.success('No tenders currently need enrichment.', { duration: 4000 });
      } else {
        toast.success(data.message || 'Enrichment process completed successfully');
      }
      
      // Refresh enrichment status and incomplete tenders
      queryClient.invalidateQueries({ queryKey: ['enrichment-status'] });
      queryClient.invalidateQueries({ queryKey: ['incomplete-tenders'] });
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to trigger enrichment');
    },
  });

  const formatDateTime = (dateString?: string) => {
    if (!dateString) return 'N/A';
    try {
      return new Date(dateString).toLocaleString('en-CA', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return 'Invalid Date';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running':
        return 'bg-blue-100 text-blue-800';
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'running':
        return <ArrowPathIcon className="w-4 h-4 animate-spin" />;
      case 'completed':
        return <CheckCircleIcon className="w-4 h-4" />;
      case 'failed':
        return <ExclamationTriangleIcon className="w-4 h-4" />;
      default:
        return <ClockIcon className="w-4 h-4" />;
    }
  };

  const handleTriggerScraper = (scraperName: string) => {
    triggerScraperMutation.mutate(scraperName);
  };

  const handleTriggerEnrichment = () => {
    triggerEnrichmentMutation.mutate(enrichmentLimit);
  };

  const logs = scraperLogs?.data || [];

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="p-6 space-y-6"
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Scraper Management</h1>
          <p className="text-gray-600 mt-1">Monitor and control the CanadaBuys tender scraper and data enrichment</p>
        </div>
        <div className="flex space-x-2">
          <button
            onClick={() => {
              queryClient.invalidateQueries({ queryKey: ['scraper-status'] });
              queryClient.invalidateQueries({ queryKey: ['scraper-logs'] });
              queryClient.invalidateQueries({ queryKey: ['enrichment-status'] });
            }}
            disabled={isRefreshingTenders}
            className="btn-secondary"
          >
            <ArrowPathIcon className={`w-4 h-4 mr-2 ${isRefreshingTenders ? 'animate-spin' : ''}`} />
            {isRefreshingTenders ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>
      </div>

      {/* Current Status Banner */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="card p-4 bg-blue-50 border border-blue-200"
      >
        <div className="flex items-center">
          <InformationCircleIcon className="w-5 h-5 text-blue-600 mr-2" />
          <div>
            <h3 className="text-sm font-medium text-blue-800">CanadaBuys Scraper</h3>
            <p className="text-sm text-blue-700 mt-1">
              The primary scraper for federal and provincial tender data with automatic province detection. 
              Fetches comprehensive tender information from the CanadaBuys portal.
            </p>
          </div>
        </div>
      </motion.div>

      {/* Tenders Refreshing Banner */}
      {isRefreshingTenders && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="card p-4 bg-green-50 border border-green-200"
        >
          <div className="flex items-center">
            <ArrowPathIcon className="w-5 h-5 text-green-600 mr-2 animate-spin" />
            <div>
              <h3 className="text-sm font-medium text-green-800">Refreshing Tenders</h3>
              <p className="text-sm text-green-700 mt-1">
                Scraper completed successfully! Updating tender data across all pages...
              </p>
            </div>
          </div>
        </motion.div>
      )}

      {/* Error Display */}
      {(statusError || logsError || enrichmentError) && (
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

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        {/* Scraper Status */}
        <div>
          <div className="card">
            <div className="p-6 border-b border-gray-200">
              <h2 className="text-xl font-semibold text-gray-900">CanadaBuys Status</h2>
            </div>
            <div className="p-6">
              {statusLoading ? (
                <div className="space-y-4">
                  <div className="animate-pulse">
                    <div className="h-16 bg-gray-200 rounded-lg"></div>
                  </div>
                </div>
              ) : scrapers.length === 0 ? (
                <div className="text-center py-8">
                  <CogIcon className="w-12 h-12 text-gray-400 mx-auto mb-2" />
                  <p className="text-gray-500">CanadaBuys scraper not found.</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {scrapers.map((scraper) => (
                    <motion.div
                      key={scraper.id}
                      className="flex items-center justify-between p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                    >
                      <div className="flex items-center space-x-4">
                        <div className="flex items-center space-x-2">
                          <GlobeAltIcon className="w-5 h-5 text-blue-600" />
                          {getStatusIcon(scraper.status)}
                          <span className={`inline-block px-2 py-1 text-xs font-semibold rounded-full ${getStatusColor(scraper.status)}`}>
                            {scraper.status}
                          </span>
                        </div>
                        <div>
                          <h3 className="font-medium text-gray-900">CanadaBuys</h3>
                          <p className="text-sm text-gray-600">
                            {scraper.total_tenders} total tenders • {scraper.recent_tenders} recent
                          </p>
                          <p className="text-xs text-gray-500 mt-1">
                            Federal and provincial tender data with automatic province detection
                          </p>
                          {scraper.error_message && (
                            <p className="text-xs text-red-600 mt-1">{scraper.error_message}</p>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center space-x-2">
                        <div className="text-right">
                          <p className="text-sm text-gray-600">Last run</p>
                          <p className="text-xs text-gray-500">{formatDateTime(scraper.last_run)}</p>
                        </div>
                        <button
                          onClick={() => handleTriggerScraper(scraper.id)}
                          disabled={scraper.status === 'running' || triggerScraperMutation.isPending}
                          className="p-2 text-gray-400 hover:text-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
                          title="Trigger scraper"
                        >
                          <PlayIcon className="w-4 h-4" />
                        </button>
                      </div>
                    </motion.div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Data Enrichment */}
        <div>
          <div className="card">
            <div className="p-6 border-b border-gray-200">
              <div className="flex items-center">
                <SparklesIcon className="w-5 h-5 text-purple-600 mr-2" />
                <h2 className="text-xl font-semibold text-gray-900">Data Enrichment</h2>
              </div>
            </div>
            <div className="p-6">
              {enrichmentLoading ? (
                <div className="space-y-4">
                  <div className="animate-pulse">
                    <div className="h-16 bg-gray-200 rounded-lg"></div>
                  </div>
                </div>
              ) : (
                <div className="space-y-4">
                  {/* Status */}
                  <div className="flex items-center justify-between p-4 bg-purple-50 rounded-lg">
                    <div className="flex items-center space-x-3">
                      <TableCellsIcon className="w-5 h-5 text-purple-600" />
                      <div>
                        <h3 className="font-medium text-purple-900">Enrichment System</h3>
                        <p className="text-sm text-purple-700">
                          {enrichmentStatus?.incomplete_tenders || 0} tenders need enrichment
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      {triggerEnrichmentMutation.isPending && (
                        <ArrowPathIcon className="w-4 h-4 animate-spin text-purple-600" />
                      )}
                      <span className={`inline-block px-2 py-1 text-xs font-semibold rounded-full ${
                        triggerEnrichmentMutation.isPending ? 'bg-blue-100 text-blue-800' :
                        enrichmentStatus?.status === 'running' ? 'bg-blue-100 text-blue-800' :
                        enrichmentStatus?.status === 'idle' ? 'bg-gray-100 text-gray-800' :
                        'bg-green-100 text-green-800'
                      }`}>
                        {triggerEnrichmentMutation.isPending ? 'processing' : (enrichmentStatus?.status || 'idle')}
                      </span>
                    </div>
                  </div>

                  {/* Settings */}
                  <div className="space-y-3">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Max Tenders to Enrich
                      </label>
                      <input
                        type="number"
                        min="1"
                        max="100"
                        value={enrichmentLimit}
                        onChange={(e) => setEnrichmentLimit(parseInt(e.target.value) || 4)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                      />
                    </div>
                  </div>

                  {/* Trigger Button */}
                  <button
                    onClick={handleTriggerEnrichment}
                    disabled={triggerEnrichmentMutation.isPending}
                    className="w-full bg-purple-600 text-white px-4 py-2 rounded-md hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    {triggerEnrichmentMutation.isPending ? (
                      <>
                        <ArrowPathIcon className="w-4 h-4 mr-2 inline animate-spin" />
                        Processing...
                      </>
                    ) : (
                      <>
                        <SparklesIcon className="w-4 h-4 mr-2 inline" />
                        Process Enrichment
                      </>
                    )}
                  </button>

                  {/* Last Result */}
                  {enrichmentStatus?.last_run && (
                    <div className="mt-4 p-3 bg-green-50 rounded-lg">
                      <p className="text-sm text-green-800">
                        Last run: {formatDateTime(enrichmentStatus.last_run)}
                      </p>
                      {enrichmentStatus.error && (
                        <p className="text-xs text-red-600 mt-1">Error: {enrichmentStatus.error}</p>
                      )}
                      {enrichmentStatus.last_result && (
                        <p className="text-xs text-green-600 mt-1">
                          {enrichmentStatus.last_result.message || 'Successfully processed'}
                        </p>
                      )}
                    </div>
                  )}

                  {/* Preview of Incomplete Tenders */}
                  {incompleteTenders?.tenders && incompleteTenders.tenders.length > 0 && (
                    <div className="mt-4 p-3 bg-gray-50 rounded-lg">
                      <h4 className="text-sm font-medium text-gray-800 mb-2">
                        Sample Tenders Needing Enrichment:
                      </h4>
                      <div className="space-y-2">
                        {incompleteTenders.tenders.slice(0, 3).map((tender, index) => (
                          <div key={tender.id} className="text-xs">
                            <p className="font-medium text-gray-700 truncate">
                              {tender.title}
                            </p>
                            <p className="text-gray-500">
                              {tender.organization} • Created: {formatDateTime(tender.created_at)}
                            </p>
                          </div>
                        ))}
                      </div>
                      {incompleteTenders.count > 3 && (
                        <p className="text-xs text-gray-500 mt-2">
                          ...and {incompleteTenders.count - 3} more tenders
                        </p>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Logs */}
      <div className="card">
        <div className="p-6 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold text-gray-900">Recent Logs</h2>
            <div className="flex space-x-2">
              <select
                value={selectedScraper || ''}
                onChange={(e) => setSelectedScraper(e.target.value || null)}
                className="px-3 py-1 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="">All Scrapers</option>
                <option value="canadabuys">CanadaBuys</option>
              </select>
            </div>
          </div>
        </div>
        <div className="p-6">
          {logsLoading ? (
            <div className="space-y-3">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="animate-pulse">
                  <div className="h-12 bg-gray-200 rounded-lg"></div>
                </div>
              ))}
            </div>
          ) : logs.length === 0 ? (
            <div className="text-center py-8">
              <DocumentTextIcon className="w-12 h-12 text-gray-400 mx-auto mb-2" />
              <p className="text-gray-500">No logs found.</p>
            </div>
          ) : (
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {logs.map((log, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.05 }}
                  className="flex items-start space-x-3 p-3 bg-gray-50 rounded-lg"
                >
                  <div className={`flex-shrink-0 w-2 h-2 rounded-full mt-2 ${
                    log.level === 'ERROR' ? 'bg-red-500' :
                    log.level === 'WARNING' ? 'bg-yellow-500' : 'bg-green-500'
                  }`} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-medium text-gray-900">{log.message}</p>
                      <span className="text-xs text-gray-500">{formatDateTime(log.timestamp)}</span>
                    </div>
                    {log.scraper && (
                      <p className="text-xs text-gray-600 mt-1 capitalize">
                        {log.scraper.replace('_', ' ')}
                      </p>
                    )}
                  </div>
                </motion.div>
              ))}
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
} 