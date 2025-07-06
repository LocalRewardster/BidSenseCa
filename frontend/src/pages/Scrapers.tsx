import React, { useState } from 'react';
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

export default function Scrapers() {
  const queryClient = useQueryClient();
  const [selectedScraper, setSelectedScraper] = useState<string | null>(null);

  // Fetch scraper status from API
  const { data: scraperStatus, isLoading: statusLoading, error: statusError } = useQuery({
    queryKey: ['scraper-status'],
    queryFn: () => apiService.getScraperStatus(),
    refetchInterval: 30000, // Refetch every 30 seconds
  });

  // Fetch scraper logs from API
  const { data: scraperLogs, isLoading: logsLoading, error: logsError } = useQuery({
    queryKey: ['scraper-logs', selectedScraper],
    queryFn: () => apiService.getScraperLogs(selectedScraper),
    refetchInterval: 30000, // Refetch every 30 seconds
  });

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
          <p className="text-gray-600 mt-1">Monitor and control the CanadaBuys tender scraper</p>
        </div>
        <div className="flex space-x-2">
          <button
            onClick={() => {
              queryClient.invalidateQueries({ queryKey: ['scraper-status'] });
              queryClient.invalidateQueries({ queryKey: ['scraper-logs'] });
            }}
            className="btn-secondary"
          >
            <ArrowPathIcon className="w-4 h-4 mr-2" />
            Refresh
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

      {/* Error Display */}
      {(statusError || logsError) && (
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

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Scraper Status */}
        <div className="lg:col-span-2">
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

        {/* Quick Stats */}
        <div>
          <div className="card">
            <div className="p-6 border-b border-gray-200">
              <h2 className="text-xl font-semibold text-gray-900">Quick Stats</h2>
            </div>
            <div className="p-6">
              {statusLoading ? (
                <div className="space-y-4">
                  {[1, 2, 3, 4].map((i) => (
                    <div key={i} className="animate-pulse">
                      <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
                      <div className="h-3 bg-gray-200 rounded w-1/2"></div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-gray-600">Scraper Status</span>
                    <span className={`text-lg font-bold ${
                      scrapers[0]?.status === 'running' ? 'text-blue-600' :
                      scrapers[0]?.status === 'completed' ? 'text-green-600' :
                      scrapers[0]?.status === 'failed' ? 'text-red-600' : 'text-gray-600'
                    }`}>
                      {scrapers[0]?.status || 'idle'}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-gray-600">Total Tenders</span>
                    <span className="text-lg font-bold text-gray-900">
                      {scrapers[0]?.total_tenders || 0}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-gray-600">Recent Tenders</span>
                    <span className="text-lg font-bold text-gray-900">
                      {scrapers[0]?.recent_tenders || 0}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-gray-600">Last Run</span>
                    <span className="text-sm text-gray-500">
                      {formatDateTime(scrapers[0]?.last_run)}
                    </span>
                  </div>
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