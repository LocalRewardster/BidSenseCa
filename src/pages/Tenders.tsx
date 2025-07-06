import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { useQuery } from '@tanstack/react-query';
import {
  Search,
  Filter,
  Download,
  Eye,
  Bookmark,
  Calendar,
  Building,
  DollarSign,
  MapPin,
  ChevronDown,
  ChevronUp,
  ChevronLeft,
  ChevronRight
} from 'lucide-react';

import Card, { CardHeader, CardTitle, CardContent } from '../components/ui/Card';
import Button from '../components/ui/Button';
import { apiService } from '../services/api';
import { Tender, TenderFilters } from '../types';

const Tenders: React.FC = () => {
  const [filters, setFilters] = useState<TenderFilters>({
    limit: 20,
    offset: 0
  });
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedProvince, setSelectedProvince] = useState('');
  const [sortBy, setSortBy] = useState('created_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');

  const { data: tendersData, isLoading } = useQuery({
    queryKey: ['tenders', filters],
    queryFn: () => apiService.getTenders(filters),
  });

  const provinces = [
    { value: '', label: 'All Provinces' },
    { value: 'federal', label: 'Federal' },
    { value: 'ontario', label: 'Ontario' },
    { value: 'alberta', label: 'Alberta' },
    { value: 'bc', label: 'British Columbia' },
    { value: 'manitoba', label: 'Manitoba' },
    { value: 'saskatchewan', label: 'Saskatchewan' },
    { value: 'quebec', label: 'Quebec' },
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

  const handleSearch = () => {
    setFilters(prev => ({
      ...prev,
      keyword: searchQuery,
      province: selectedProvince,
      offset: 0
    }));
  };

  const handleSort = (field: string) => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(field);
      setSortOrder('desc');
    }
  };

  const handlePageChange = (newOffset: number) => {
    setFilters(prev => ({
      ...prev,
      offset: newOffset
    }));
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
            Tenders
          </h1>
          <p className="text-gray-600">
            Browse and search through all available tenders across Canada.
          </p>
        </motion.div>

        <motion.div
          className="px-6 pb-8"
          variants={containerVariants}
          initial="hidden"
          animate="visible"
        >
          {/* Search and Filters */}
          <motion.div variants={itemVariants} className="mb-6">
            <Card>
              <CardContent className="p-6">
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                  {/* Search */}
                  <div className="md:col-span-2">
                    <div className="relative">
                      <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
                      <input
                        type="text"
                        placeholder="Search tenders by title, description, or organization..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                        className="w-full pl-10 pr-4 py-3 bg-white/20 backdrop-blur-sm border border-white/30 rounded-xl 
                                   text-gray-700 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 
                                   focus:border-blue-500 transition-all duration-300"
                      />
                    </div>
                  </div>

                  {/* Province Filter */}
                  <div>
                    <select
                      value={selectedProvince}
                      onChange={(e) => setSelectedProvince(e.target.value)}
                      className="w-full px-4 py-3 bg-white/20 backdrop-blur-sm border border-white/30 rounded-xl 
                                 text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500/50 
                                 focus:border-blue-500 transition-all duration-300"
                    >
                      {provinces.map((province) => (
                        <option key={province.value} value={province.value}>
                          {province.label}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Search Button */}
                  <div>
                    <Button
                      variant="primary"
                      onClick={handleSearch}
                      className="w-full"
                    >
                      Search
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>

          {/* Results Header */}
          <motion.div variants={itemVariants} className="mb-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl font-semibold text-gray-900">
                  {isLoading ? 'Loading...' : `${tendersData?.total || 0} tenders found`}
                </h2>
                <p className="text-gray-600">
                  Showing {filters.offset + 1} to {Math.min(filters.offset + (filters.limit || 20), tendersData?.total || 0)} of {tendersData?.total || 0} results
                </p>
              </div>
              <Button variant="secondary" size="sm">
                <Download className="w-4 h-4 mr-2" />
                Export
              </Button>
            </div>
          </motion.div>

          {/* Tenders Table */}
          <motion.div variants={itemVariants}>
            <Card>
              <CardContent className="p-0">
                {isLoading ? (
                  <div className="p-6">
                    <div className="space-y-4">
                      {[...Array(5)].map((_, i) => (
                        <div key={i} className="loading-pulse h-20 rounded-lg"></div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead className="bg-gray-50 border-b border-gray-200">
                        <tr>
                          <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                              onClick={() => handleSort('title')}>
                            <div className="flex items-center">
                              Title
                              {sortBy === 'title' && (
                                sortOrder === 'asc' ? <ChevronUp className="w-4 h-4 ml-1" /> : <ChevronDown className="w-4 h-4 ml-1" />
                              )}
                            </div>
                          </th>
                          <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                              onClick={() => handleSort('organization')}>
                            <div className="flex items-center">
                              Organization
                              {sortBy === 'organization' && (
                                sortOrder === 'asc' ? <ChevronUp className="w-4 h-4 ml-1" /> : <ChevronDown className="w-4 h-4 ml-1" />
                              )}
                            </div>
                          </th>
                          <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                              onClick={() => handleSort('closing_date')}>
                            <div className="flex items-center">
                              Closing Date
                              {sortBy === 'closing_date' && (
                                sortOrder === 'asc' ? <ChevronUp className="w-4 h-4 ml-1" /> : <ChevronDown className="w-4 h-4 ml-1" />
                              )}
                            </div>
                          </th>
                          <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Value
                          </th>
                          <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Source
                          </th>
                          <th className="px-6 py-4 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Actions
                          </th>
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-gray-200">
                        {tendersData?.tenders.map((tender) => (
                          <motion.tr
                            key={tender.id}
                            className="hover:bg-gray-50 transition-colors duration-200"
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            whileHover={{ scale: 1.01 }}
                          >
                            <td className="px-6 py-4">
                              <div>
                                <div className="text-sm font-medium text-gray-900 line-clamp-2">
                                  {tender.title}
                                </div>
                                {tender.reference && (
                                  <div className="text-sm text-gray-500">
                                    Ref: {tender.reference}
                                  </div>
                                )}
                              </div>
                            </td>
                            <td className="px-6 py-4">
                              <div className="flex items-center">
                                <Building className="w-4 h-4 text-gray-400 mr-2" />
                                <span className="text-sm text-gray-900">
                                  {tender.organization || 'N/A'}
                                </span>
                              </div>
                            </td>
                            <td className="px-6 py-4">
                              <div className="flex items-center">
                                <Calendar className="w-4 h-4 text-gray-400 mr-2" />
                                <span className="text-sm text-gray-900">
                                  {tender.closing_date ? formatDate(tender.closing_date) : 'N/A'}
                                </span>
                              </div>
                            </td>
                            <td className="px-6 py-4">
                              <div className="flex items-center">
                                <DollarSign className="w-4 h-4 text-gray-400 mr-2" />
                                <span className="text-sm text-gray-900">
                                  {formatValue(tender.contract_value)}
                                </span>
                              </div>
                            </td>
                            <td className="px-6 py-4">
                              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 capitalize">
                                {tender.source_name.replace(/([A-Z])/g, ' $1').trim()}
                              </span>
                            </td>
                            <td className="px-6 py-4 text-right">
                              <div className="flex items-center justify-end space-x-2">
                                <Button variant="ghost" size="sm">
                                  <Eye className="w-4 h-4" />
                                </Button>
                                <Button variant="ghost" size="sm">
                                  <Bookmark className="w-4 h-4" />
                                </Button>
                              </div>
                            </td>
                          </motion.tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </CardContent>
            </Card>
          </motion.div>

          {/* Pagination */}
          {tendersData && tendersData.total > (filters.limit || 20) && (
            <motion.div variants={itemVariants} className="mt-6">
              <Card>
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div className="text-sm text-gray-700">
                      Showing {filters.offset + 1} to {Math.min(filters.offset + (filters.limit || 20), tendersData.total)} of {tendersData.total} results
                    </div>
                    <div className="flex items-center space-x-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        disabled={filters.offset === 0}
                        onClick={() => handlePageChange(Math.max(0, filters.offset - (filters.limit || 20)))}
                      >
                        <ChevronLeft className="w-4 h-4" />
                        Previous
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        disabled={filters.offset + (filters.limit || 20) >= tendersData.total}
                        onClick={() => handlePageChange(filters.offset + (filters.limit || 20))}
                      >
                        Next
                        <ChevronRight className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          )}
        </motion.div>
      </div>
    </div>
  );
};

export default Tenders; 