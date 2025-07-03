import { Link } from 'react-router-dom'
import { Search, Bookmark, Settings, LogOut } from 'lucide-react'

const Navbar = () => {
  return (
    <nav className="bg-white dark:bg-gray-800 shadow-sm border-b">
      <div className="container mx-auto px-4">
        <div className="flex justify-between items-center h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center space-x-2">
            <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-sm">BS</span>
            </div>
            <span className="text-xl font-bold text-gray-900 dark:text-white">
              BidSense
            </span>
          </Link>

          {/* Navigation Links */}
          <div className="hidden md:flex items-center space-x-8">
            <Link 
              to="/" 
              className="text-gray-700 dark:text-gray-300 hover:text-primary transition-colors"
            >
              Dashboard
            </Link>
            <Link 
              to="/tenders" 
              className="text-gray-700 dark:text-gray-300 hover:text-primary transition-colors"
            >
              Tenders
            </Link>
            <Link 
              to="/bookmarks" 
              className="text-gray-700 dark:text-gray-300 hover:text-primary transition-colors flex items-center space-x-1"
            >
              <Bookmark size={16} />
              <span>Bookmarks</span>
            </Link>
          </div>

          {/* Right side actions */}
          <div className="flex items-center space-x-4">
            <button className="p-2 text-gray-700 dark:text-gray-300 hover:text-primary transition-colors">
              <Search size={20} />
            </button>
            <button className="p-2 text-gray-700 dark:text-gray-300 hover:text-primary transition-colors">
              <Settings size={20} />
            </button>
            <button className="p-2 text-gray-700 dark:text-gray-300 hover:text-red-500 transition-colors">
              <LogOut size={20} />
            </button>
          </div>
        </div>
      </div>
    </nav>
  )
}

export default Navbar 