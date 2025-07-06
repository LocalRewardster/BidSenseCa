import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  Home,
  Search,
  BarChart3,
  Settings,
  Play,
  Database,
  Users,
  Bell,
  Menu,
  X,
  TrendingUp,
  FileText,
  Calendar,
  MapPin
} from 'lucide-react';

interface NavItem {
  name: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: number;
}

const navigation: NavItem[] = [
  { name: 'Dashboard', href: '/', icon: Home },
  { name: 'Tenders', href: '/tenders', icon: FileText },
  { name: 'Search', href: '/search', icon: Search },
  { name: 'Analytics', href: '/analytics', icon: BarChart3 },
  { name: 'Scrapers', href: '/scrapers', icon: Database },
  { name: 'Jobs', href: '/jobs', icon: Play },
  { name: 'Reports', href: '/reports', icon: TrendingUp },
  { name: 'Calendar', href: '/calendar', icon: Calendar },
  { name: 'Map', href: '/map', icon: MapPin },
  { name: 'Users', href: '/users', icon: Users },
  { name: 'Settings', href: '/settings', icon: Settings },
];

const Sidebar: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false);
  const location = useLocation();

  return (
    <>
      {/* Mobile menu button */}
      <div className="lg:hidden fixed top-4 left-4 z-50">
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="p-2 rounded-lg bg-white/20 backdrop-blur-sm border border-white/30 text-gray-700 hover:bg-white/30 transition-all"
        >
          {collapsed ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </div>

      {/* Sidebar */}
      <motion.div
        className={`fixed inset-y-0 left-0 z-40 bg-white/10 backdrop-blur-xl border-r border-white/20 
                   ${collapsed ? 'w-16' : 'w-64'} transition-all duration-300 ease-in-out`}
        initial={{ x: -100 }}
        animate={{ x: 0 }}
        transition={{ duration: 0.3 }}
      >
        <div className="flex flex-col h-full">
          {/* Logo */}
          <div className="flex items-center justify-center h-16 px-4">
            <motion.div
              className="flex items-center space-x-3"
              whileHover={{ scale: 1.05 }}
            >
              <div className="w-8 h-8 bg-gradient-to-r from-blue-600 to-purple-600 rounded-lg flex items-center justify-center">
                <TrendingUp className="w-5 h-5 text-white" />
              </div>
              {!collapsed && (
                <motion.span
                  className="text-xl font-bold text-gradient-primary"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.1 }}
                >
                  BidSense
                </motion.span>
              )}
            </motion.div>
          </div>

          {/* Navigation */}
          <nav className="flex-1 px-4 space-y-2">
            {navigation.map((item) => {
              const isActive = location.pathname === item.href;
              
              return (
                <motion.div
                  key={item.name}
                  whileHover={{ x: 5 }}
                  whileTap={{ scale: 0.95 }}
                >
                  <Link
                    to={item.href}
                    className={`flex items-center px-3 py-3 rounded-xl text-sm font-medium transition-all duration-200 group relative
                               ${isActive 
                                 ? 'bg-gradient-to-r from-blue-600 to-purple-600 text-white shadow-lg' 
                                 : 'text-gray-700 hover:bg-white/20 hover:text-gray-900'
                               }`}
                  >
                    <item.icon className={`w-5 h-5 ${collapsed ? 'mx-auto' : 'mr-3'}`} />
                    {!collapsed && (
                      <motion.span
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.1 }}
                      >
                        {item.name}
                      </motion.span>
                    )}
                    {item.badge && !collapsed && (
                      <span className="ml-auto bg-red-500 text-white text-xs rounded-full px-2 py-1">
                        {item.badge}
                      </span>
                    )}
                    {isActive && (
                      <motion.div
                        className="absolute left-0 top-1/2 transform -translate-y-1/2 w-1 h-8 bg-white rounded-r-full"
                        layoutId="activeTab"
                        initial={false}
                        transition={{ type: "spring", stiffness: 300, damping: 30 }}
                      />
                    )}
                  </Link>
                </motion.div>
              );
            })}
          </nav>

          {/* Bottom section */}
          <div className="p-4 border-t border-white/20">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-gradient-to-r from-green-500 to-emerald-600 rounded-full flex items-center justify-center">
                <Bell className="w-4 h-4 text-white" />
              </div>
              {!collapsed && (
                <div className="flex-1">
                  <p className="text-sm font-medium text-gray-700">Notifications</p>
                  <p className="text-xs text-gray-500">3 new alerts</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </motion.div>

      {/* Overlay for mobile */}
      {!collapsed && (
        <motion.div
          className="fixed inset-0 bg-black/20 backdrop-blur-sm z-30 lg:hidden"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={() => setCollapsed(true)}
        />
      )}
    </>
  );
};

export default Sidebar; 