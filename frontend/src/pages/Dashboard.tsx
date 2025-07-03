import { useQuery } from '@tanstack/react-query'
import { TrendingUp, Calendar, MapPin, DollarSign } from 'lucide-react'

const Dashboard = () => {
  // TODO: Replace with actual API calls
  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: () => Promise.resolve({
      totalTenders: 1247,
      newToday: 23,
      bookmarked: 12,
      matchingTenders: 8
    })
  })

  const { data: recentTenders, isLoading: tendersLoading } = useQuery({
    queryKey: ['recent-tenders'],
    queryFn: () => Promise.resolve([
      {
        id: '1',
        title: 'Highway Construction Project - Phase 2',
        buyer: 'Ministry of Transportation',
        province: 'Ontario',
        deadline: '2025-02-15',
        value: '$2.5M - $5M'
      },
      {
        id: '2',
        title: 'Office Building Renovation Services',
        buyer: 'City of Vancouver',
        province: 'British Columbia',
        deadline: '2025-02-20',
        value: '$500K - $1M'
      },
      {
        id: '3',
        title: 'Waste Management Facility Construction',
        buyer: 'Alberta Infrastructure',
        province: 'Alberta',
        deadline: '2025-02-25',
        value: '$5M - $10M'
      }
    ])
  })

  if (statsLoading || tendersLoading) {
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
          Dashboard
        </h1>
        <p className="text-gray-600 dark:text-gray-400">
          Welcome back! Here's what's happening with your tenders.
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="card">
          <div className="flex items-center">
            <div className="p-2 bg-blue-100 rounded-lg">
              <TrendingUp className="h-6 w-6 text-blue-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">
                Total Tenders
              </p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {stats?.totalTenders.toLocaleString()}
              </p>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center">
            <div className="p-2 bg-green-100 rounded-lg">
              <Calendar className="h-6 w-6 text-green-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">
                New Today
              </p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {stats?.newToday}
              </p>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center">
            <div className="p-2 bg-yellow-100 rounded-lg">
              <MapPin className="h-6 w-6 text-yellow-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">
                Bookmarked
              </p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {stats?.bookmarked}
              </p>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center">
            <div className="p-2 bg-purple-100 rounded-lg">
              <DollarSign className="h-6 w-6 text-purple-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600 dark:text-gray-400">
                Matching
              </p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {stats?.matchingTenders}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Tenders */}
      <div className="card">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            Recent Tenders
          </h2>
          <button className="text-primary hover:text-primary/80 text-sm font-medium">
            View All
          </button>
        </div>

        <div className="space-y-4">
          {recentTenders?.map((tender) => (
            <div
              key={tender.id}
              className="flex items-center justify-between p-4 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
            >
              <div className="flex-1">
                <h3 className="font-medium text-gray-900 dark:text-white">
                  {tender.title}
                </h3>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  {tender.buyer} • {tender.province}
                </p>
              </div>
              <div className="text-right">
                <p className="text-sm font-medium text-gray-900 dark:text-white">
                  {tender.value}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-500">
                  Due: {tender.deadline}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export default Dashboard 