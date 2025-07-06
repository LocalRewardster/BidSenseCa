import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useQuery } from '@tanstack/react-query';
import {
  TrendingUp,
  FileText,
  Database,
  DollarSign,
  Calendar,
  MapPin,
  ArrowUpRight,
  Clock,
  Building
} from 'lucide-react';

import StatCard from '../components/ui/StatCard';
import Card, { CardHeader, CardTitle, CardContent } from '../components/ui/Card';
import Button from '../components/ui/Button';
import { apiService } from '../services/api';
import { Tender, TenderStatistics, ScraperStatus } from '../types';

const Dashboard: React.FC = () => {
  const [recentTenders, setRecentTenders] = useState<Tender[]>([]);

  // Fetch dashboard data
  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['tender-statistics'],
    queryFn: () => apiService.getTenderStatistics(),
  });

  const { data: sources, isLoading: sourcesLoading } = useQuery({
    queryKey: ['scraper-sources'],
    queryFn: () => apiService.getAvailableSources(),
  });

  const { data: tenders, isLoading: tendersLoading } = useQuery({
    queryKey: ['recent-tenders'],
    queryFn: () => apiService.getTenders({ limit: 5 }),
  });

  useEffect(() => {
    if (tenders) {
      setRecentTenders(tenders.tenders);
    }
  }, [tenders]);

  // Mock data for demonstration
  const mockStats = {
    total_tenders: 1247,
    recent_tenders: 89,
    active_scrapers: 7,
    total_value: '$2.4M'
  };

  const mockSources = [
    { scraper_name: 'canadabuys', total_tenders: 456, is_enabled: true },
    { scraper_name: 'ontario', total_tenders: 234, is_enabled: true },
    { scraper_name: 'apc', total_tenders: 189, is_enabled: true },
    { scraper_name: 'bcbid', total_tenders: 156, is_enabled: true },
    { scraper_name: 'manitoba', total_tenders: 98, is_enabled: true },
    { scraper_name: 'saskatchewan', total_tenders: 87, is_enabled: true },
    { scraper_name: 'quebec', total_tenders: 67, is_enabled: true },
  ];

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-CA', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  const formatValue = (value: string) => {
    if (!value) return 'N/A';
    return value;
  };

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1
      }
    }
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0 }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100">
      <div className="lg:ml-64">
        {/* Header */}
        <motion.div
          className="p-6"
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <h1 className="text-3xl font-bold text-gradient-primary mb-2">
            Welcome back, John! 👋
          </h1>
          <p className="text-gray-600">
            Here's what's happening with your tender intelligence today.
          </p>
        </motion.div>

        {/* Statistics Cards */}
        <motion.div
          className="px-6 mb-8"
          variants={containerVariants}
          initial="hidden"
          animate="visible"
        >
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <motion.div variants={itemVariants}>
              <StatCard
                title="Total Tenders"
                value={stats?.total_tenders || mockStats.total_tenders}
                change={12}
                changeType="increase"
                icon={<FileText className="w-6 h-6" />}
                color="blue"
                loading={statsLoading}
              />
            </motion.div>
            <motion.div variants={itemVariants}>
              <StatCard
                title="Recent Tenders"
                value={stats?.recent_tenders || mockStats.recent_tenders}
                change={8}
                changeType="increase"
                icon={<Clock className="w-6 h-6" />}
                color="green"
                loading={statsLoading}
              />
            </motion.div>
            <motion.div variants={itemVariants}>
              <StatCard
                title="Active Scrapers"
                value={mockStats.active_scrapers}
                change={0}
                changeType="neutral"
                icon={<Database className="w-6 h-6" />}
                color="purple"
                loading={sourcesLoading}
              />
            </motion.div>
            <motion.div variants={itemVariants}>
              <StatCard
                title="Total Value"
                value={mockStats.total_value}
                change={15}
                changeType="increase"
                icon={<DollarSign className="w-6 h-6" />}
                color="orange"
                loading={statsLoading}
              />
            </motion.div>
          </div>
        </motion.div>

        {/* Main Content */}
        <div className="px-6 pb-8">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Recent Tenders */}
            <motion.div
              className="lg:col-span-2"
              variants={itemVariants}
              initial="hidden"
              animate="visible"
            >
              <Card>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle>Recent Tenders</CardTitle>
                    <Button variant="ghost" size="sm">
                      View All
                      <ArrowUpRight className="w-4 h-4 ml-1" />
                    </Button>
                  </div>
                </CardHeader>
                <CardContent>
                  {tendersLoading ? (
                    <div className="space-y-4">
                      {[...Array(5)].map((_, i) => (
                        <div key={i} className="loading-pulse h-20 rounded-lg"></div>
                      ))}
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {recentTenders.map((tender) => (
                        <motion.div
                          key={tender.id}
                          className="p-4 border border-gray-200 rounded-xl hover:bg-gray-50 transition-all duration-200 cursor-pointer"
                          whileHover={{ x: 5 }}
                        >
                          <div className="flex items-start justify-between">
                            <div className="flex-1">
                              <h3 className="font-semibold text-gray-900 mb-1 line-clamp-2">
                                {tender.title}
                              </h3>
                              <div className="flex items-center space-x-4 text-sm text-gray-600">
                                {tender.organization && (
                                  <div className="flex items-center">
                                    <Building className="w-4 h-4 mr-1" />
                                    {tender.organization}
                                  </div>
                                )}
                                {tender.closing_date && (
                                  <div className="flex items-center">
                                    <Calendar className="w-4 h-4 mr-1" />
                                    {formatDate(tender.closing_date)}
                                  </div>
                                )}
                                {tender.contract_value && (
                                  <div className="flex items-center">
                                    <DollarSign className="w-4 h-4 mr-1" />
                                    {formatValue(tender.contract_value)}
                                  </div>
                                )}
                              </div>
                            </div>
                            <div className="ml-4">
                              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                                {tender.source_name}
                              </span>
                            </div>
                          </div>
                        </motion.div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            </motion.div>

            {/* Scraper Status */}
            <motion.div
              variants={itemVariants}
              initial="hidden"
              animate="visible"
            >
              <Card>
                <CardHeader>
                  <CardTitle>Scraper Status</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {mockSources.map((source) => (
                      <div key={source.scraper_name} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                        <div className="flex items-center space-x-3">
                          <div className={`w-3 h-3 rounded-full ${source.is_enabled ? 'bg-green-500' : 'bg-red-500'}`}></div>
                          <div>
                            <p className="font-medium text-gray-900 capitalize">
                              {source.scraper_name.replace(/([A-Z])/g, ' $1').trim()}
                            </p>
                            <p className="text-sm text-gray-600">{source.total_tenders} tenders</p>
                          </div>
                        </div>
                        <span className={`text-xs px-2 py-1 rounded-full ${
                          source.is_enabled 
                            ? 'bg-green-100 text-green-800' 
                            : 'bg-red-100 text-red-800'
                        }`}>
                          {source.is_enabled ? 'Active' : 'Inactive'}
                        </span>
                      </div>
                    ))}
                  </div>
                  <div className="mt-6">
                    <Button variant="primary" className="w-full">
                      Run All Scrapers
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          </div>

          {/* Quick Actions */}
          <motion.div
            className="mt-8"
            variants={itemVariants}
            initial="hidden"
            animate="visible"
          >
            <Card>
              <CardHeader>
                <CardTitle>Quick Actions</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <Button variant="primary" className="h-16 flex-col">
                    <Search className="w-6 h-6 mb-2" />
                    Advanced Search
                  </Button>
                  <Button variant="secondary" className="h-16 flex-col">
                    <BarChart3 className="w-6 h-6 mb-2" />
                    View Analytics
                  </Button>
                  <Button variant="success" className="h-16 flex-col">
                    <Database className="w-6 h-6 mb-2" />
                    Manage Scrapers
                  </Button>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard; 