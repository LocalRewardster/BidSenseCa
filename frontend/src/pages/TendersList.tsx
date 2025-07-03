import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Search, Filter, Bookmark, Calendar, MapPin } from 'lucide-react'

const TendersList = () => {
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedProvince, setSelectedProvince] = useState('')
  const [selectedNAICS, setSelectedNAICS] = useState('')

  // TODO: Replace with actual API calls
  const { data: tenders, isLoading } = useQuery({
    queryKey: ['tenders', searchTerm, selectedProvince, selectedNAICS],
    queryFn: () => Promise.resolve([
      {
        id: '1',
        title: 'Highway Construction Project - Phase 2',
        buyer: 'Ministry of Transportation',
        province: 'Ontario',
        naics: '237310',
        deadline: '2025-02-15',
        value: '$2.5M - $5M',
        summary: 'Major highway construction project including bridge repairs and road widening.',
        tags: ['construction', 'highway', 'infrastructure']
      },
      {
        id: '2',
        title: 'Office Building Renovation Services',
        buyer: 'City of Vancouver',
        province: 'British Columbia',
        naics: '238220',
        deadline: '2025-02-20',
        value: '$500K - $1M',
        summary: 'Complete renovation of municipal office building including HVAC and electrical systems.',
        tags: ['renovation', 'office', 'HVAC']
      },
      {
        id: '3',
        title: 'Waste Management Facility Construction',
        buyer: 'Alberta Infrastructure',
        province: 'Alberta',
        naics: '237990',
        deadline: '2025-02-25',
        value: '$5M - $10M',
        summary: 'Construction of new waste processing and recycling facility.',
        tags: ['waste management', 'facility', 'recycling']
      }
    ])
  })

  const provinces = [
    'Alberta', 'British Columbia', 'Manitoba', 'New Brunswick',
    'Newfoundland and Labrador', 'Nova Scotia', 'Ontario',
    'Prince Edward Island', 'Quebec', 'Saskatchewan'
  ]

  const naicsCodes = [
    { code: '237310', description: 'Highway, Street, and Bridge Construction' },
    { code: '238220', description: 'Plumbing, Heating, and Air-Conditioning Contractors' },
    { code: '237990', description: 'Other Heavy and Civil Engineering Construction' },
    { code: '236220', description: 'Commercial and Institutional Building Construction' }
  ]

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="loading-spinner"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
          Tenders
        </h1>
        <p className="text-gray-600 dark:text-gray-400">
          Discover and track government tenders across Canada
        </p>
      </div>

      {/* Filters */}
      <div className="card">
        <div className="flex flex-col lg:flex-row gap-4">
          {/* Search */}
          <div className="flex-1">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
              <input
                type="text"
                placeholder="Search tenders..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
              />
            </div>
          </div>

          {/* Province Filter */}
          <div className="lg:w-48">
            <select
              value={selectedProvince}
              onChange={(e) => setSelectedProvince(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
            >
              <option value="">All Provinces</option>
              {provinces.map((province) => (
                <option key={province} value={province}>
                  {province}
                </option>
              ))}
            </select>
          </div>

          {/* NAICS Filter */}
          <div className="lg:w-64">
            <select
              value={selectedNAICS}
              onChange={(e) => setSelectedNAICS(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
            >
              <option value="">All NAICS Codes</option>
              {naicsCodes.map((naics) => (
                <option key={naics.code} value={naics.code}>
                  {naics.code} - {naics.description}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Results */}
      <div className="space-y-4">
        {tenders?.map((tender) => (
          <div
            key={tender.id}
            className="card hover:shadow-lg transition-shadow cursor-pointer"
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center space-x-2 mb-2">
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                    {tender.title}
                  </h3>
                  <button className="p-1 text-gray-400 hover:text-yellow-500 transition-colors">
                    <Bookmark size={16} />
                  </button>
                </div>
                
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
                  {tender.summary}
                </p>

                <div className="flex items-center space-x-4 text-sm text-gray-500 dark:text-gray-500">
                  <div className="flex items-center space-x-1">
                    <MapPin size={14} />
                    <span>{tender.province}</span>
                  </div>
                  <div className="flex items-center space-x-1">
                    <Calendar size={14} />
                    <span>Due: {tender.deadline}</span>
                  </div>
                  <span className="font-medium text-gray-900 dark:text-white">
                    {tender.value}
                  </span>
                </div>

                <div className="flex flex-wrap gap-2 mt-3">
                  {tender.tags.map((tag) => (
                    <span
                      key={tag}
                      className="px-2 py-1 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 text-xs rounded-full"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {tenders?.length === 0 && (
        <div className="text-center py-12">
          <p className="text-gray-500 dark:text-gray-400">
            No tenders found matching your criteria.
          </p>
        </div>
      )}
    </div>
  )
}

export default TendersList 