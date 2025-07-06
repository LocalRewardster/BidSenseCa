import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  DocumentTextIcon,
  CurrencyDollarIcon,
  ClockIcon,
  MapPinIcon,
  ChartBarIcon,
  EyeIcon,
  CogIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';
import { apiService, Tender, TenderStatistics } from '../services/api';

export default function Dashboard() {
  const navigate = useNavigate();
  
  // Fetch statistics
  const { 
    data: stats, 
    isLoading: statsLoading, 
    error: statsError,
    refetch: refetchStats 
  } = useQuery<TenderStatistics>({
    queryKey: ['tender-stats'],
    queryFn: () => apiService.getTenderStatistics(),
    refetchInterval: 30000, // Refetch every 30 seconds
  });

  // Fetch recent tenders (limit 5)
  const { 
    data: tendersData, 
    isLoading: tendersLoading, 
    error: tendersError,
    refetch: refetchTenders 
  } = useQuery<{ tenders: Tender[] }>({
    queryKey: ['recent-tenders'],
    queryFn: () => apiService.getTenders({ limit: 5, offset: 0 }),
    select: (data) => ({ tenders: data.tenders }),
    refetchInterval: 30000, // Refetch every 30 seconds
  });

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

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="p-6 space-y-6"
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-600 mt-1">Welcome to your Canadian Opportunity Intelligence platform!</p>
        </div>
        <div className="flex space-x-2">
          <button
            onClick={() => {
              refetchStats();
              refetchTenders();
            }}
            className="btn-secondary"
          >
            <ChartBarIcon className="w-4 h-4 mr-2" />
            Refresh
          </button>
        </div>
      </div>

      {/* Error Display */}
      {(statsError || tendersError) && (
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
                Unable to connect to the backend API. Please ensure the backend server is running on http://localhost:8000
              </p>
            </div>
          </div>
        </motion.div>
      )}

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <motion.div className="card p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Total Tenders</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">
                {statsLoading ? '...' : stats?.total_tenders ?? 'N/A'}
              </p>
            </div>
            <div className="p-3 rounded-lg bg-blue-100">
              <DocumentTextIcon className="w-6 h-6 text-blue-600" />
            </div>
          </div>
        </motion.div>
        <motion.div className="card p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Recent Tenders</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">
                {statsLoading ? '...' : stats?.recent_tenders ?? 'N/A'}
              </p>
            </div>
            <div className="p-3 rounded-lg bg-green-100">
              <ClockIcon className="w-6 h-6 text-green-600" />
            </div>
          </div>
        </motion.div>
        <motion.div className="card p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Sources</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">
                {statsLoading ? '...' : Object.keys(stats?.source_counts || {}).length}
              </p>
            </div>
            <div className="p-3 rounded-lg bg-purple-100">
              <CogIcon className="w-6 h-6 text-purple-600" />
            </div>
          </div>
        </motion.div>
        <motion.div className="card p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Last Updated</p>
              <p className="text-sm font-bold text-gray-900 mt-1">
                {statsLoading ? '...' : formatDateTime(stats?.last_updated)}
              </p>
            </div>
            <div className="p-3 rounded-lg bg-emerald-100">
              <CheckCircleIcon className="w-6 h-6 text-emerald-600" />
            </div>
          </div>
        </motion.div>
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Tenders */}
        <div className="lg:col-span-2">
          <motion.div className="card">
            <div className="p-6 border-b border-gray-200">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-semibold text-gray-900">Recent Tenders</h2>
                <button 
                  onClick={() => navigate('/tenders')}
                  className="text-blue-600 hover:text-blue-800 text-sm font-medium"
                >
                  View All
                </button>
              </div>
            </div>
            <div className="p-6">
              {tendersLoading ? (
                <div className="flex items-center justify-center py-8">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                  <span className="ml-2 text-gray-600">Loading tenders...</span>
                </div>
              ) : tendersError ? (
                <div className="text-center py-8">
                  <ExclamationTriangleIcon className="w-12 h-12 text-red-400 mx-auto mb-2" />
                  <p className="text-red-500">Failed to load tenders.</p>
                </div>
              ) : tendersData?.tenders.length === 0 ? (
                <div className="text-center py-8">
                  <DocumentTextIcon className="w-12 h-12 text-gray-400 mx-auto mb-2" />
                  <p className="text-gray-500">No tenders found.</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {tendersData?.tenders.map((tender) => (
                    <motion.div
                      key={tender.id}
                      className="flex items-center justify-between p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors cursor-pointer"
                      onClick={() => navigate(`/tenders/${tender.id}`)}
                    >
                      <div className="flex-1 min-w-0">
                        <h3 className="font-medium text-gray-900 truncate">{tender.title}</h3>
                        <p className="text-sm text-gray-600 truncate">{tender.organization}</p>
                        {tender.description && (
                          <p className="text-xs text-gray-500 mt-1 line-clamp-2">{tender.description}</p>
                        )}
                      </div>
                      <div className="text-right ml-4">
                        <p className="font-medium text-gray-900 text-sm">
                          {tender.contract_value || 'N/A'}
                        </p>
                        <p className="text-sm text-gray-600">
                          {formatDate(tender.closing_date)}
                        </p>
                        <span className={`inline-block px-2 py-1 text-xs font-semibold rounded-full mt-1 ${getStatusColor(tender)}`}>
                          {getStatusText(tender)}
                        </span>
                      </div>
                      <span className="ml-4 px-2 py-1 text-xs font-semibold rounded-full bg-blue-100 text-blue-800 capitalize">
                        {tender.source_name}
                      </span>
                    </motion.div>
                  ))}
                </div>
              )}
            </div>
          </motion.div>
        </div>

        {/* Search Status */}
        <div>
          <motion.div className="card">
            <div className="p-6 border-b border-gray-200">
              <h2 className="text-xl font-semibold text-gray-900">Source Status</h2>
            </div>
            <div className="p-6">
              {statsLoading ? (
                <div className="space-y-3">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="animate-pulse">
                      <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
                      <div className="h-3 bg-gray-200 rounded w-1/2"></div>
                    </div>
                  ))}
                </div>
              ) : stats?.source_counts ? (
                <div className="space-y-3">
                  {Object.entries(stats.source_counts).map(([source, count]) => (
                    <div key={source} className="flex items-center justify-between">
                      <div>
                        <p className="font-medium text-gray-900 capitalize">{source}</p>
                        <p className="text-sm text-gray-600">{count} tenders</p>
                      </div>
                      <div className="flex items-center">
                        <div className="w-2 h-2 rounded-full mr-2 bg-green-500" />
                        <span className="text-sm text-gray-600">Active</span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-4">
                  <p className="text-gray-500">No source data available</p>
                </div>
              )}
            </div>
          </motion.div>
        </div>
      </div>

      {/* Quick Actions */}
      <motion.div className="card p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Quick Actions</h2>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <button 
            onClick={() => navigate('/tenders')}
            className="flex items-center justify-center p-4 bg-blue-50 hover:bg-blue-100 rounded-lg transition-colors"
          >
            <DocumentTextIcon className="w-6 h-6 text-blue-600 mr-2" />
            <span className="font-medium text-blue-900">View Tenders</span>
          </button>
          <button 
            onClick={() => navigate('/scrapers')}
            className="flex items-center justify-center p-4 bg-green-50 hover:bg-green-100 rounded-lg transition-colors"
          >
            <ChartBarIcon className="w-6 h-6 text-green-600 mr-2" />
            <span className="font-medium text-green-900">Run Scrapers</span>
          </button>
          <button className="flex items-center justify-center p-4 bg-purple-50 hover:bg-purple-100 rounded-lg transition-colors">
            <EyeIcon className="w-6 h-6 text-purple-600 mr-2" />
            <span className="font-medium text-purple-900">View Reports</span>
          </button>
          <button className="flex items-center justify-center p-4 bg-orange-50 hover:bg-orange-100 rounded-lg transition-colors">
            <CogIcon className="w-6 h-6 text-orange-600 mr-2" />
            <span className="font-medium text-orange-900">Settings</span>
          </button>
        </div>
      </motion.div>
    </motion.div>
  );
} 