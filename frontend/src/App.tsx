import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'react-hot-toast';
import { motion, AnimatePresence } from 'framer-motion';

import Sidebar from './components/layout/Sidebar';
import Header from './components/layout/Header';
import Dashboard from './pages/Dashboard';
import Tenders from './pages/Tenders';
import TenderDetail from './pages/TenderDetail';
import Scrapers from './pages/Scrapers';
import './styles/globals.css';

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      retry: 1,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <div className="flex h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100">
          {/* Sidebar */}
          <Sidebar />
          
          {/* Main Content */}
          <div className="flex-1 flex flex-col lg:ml-64">
            {/* Header */}
            <Header />
            
            {/* Page Content */}
            <main className="flex-1 overflow-auto">
              <AnimatePresence mode="wait">
                <Routes>
                  <Route path="/" element={<Dashboard />} />
                  <Route path="/tenders" element={<Tenders />} />
                  <Route path="/tenders/:id" element={<TenderDetail />} />
                  <Route path="/scrapers" element={<Scrapers />} />
                  <Route path="/search" element={<div className="p-6">Search Page (Coming Soon)</div>} />
                  <Route path="/analytics" element={<div className="p-6">Analytics Page (Coming Soon)</div>} />
                  <Route path="/jobs" element={<div className="p-6">Jobs Page (Coming Soon)</div>} />
                  <Route path="/reports" element={<div className="p-6">Reports Page (Coming Soon)</div>} />
                  <Route path="/calendar" element={<div className="p-6">Calendar Page (Coming Soon)</div>} />
                  <Route path="/map" element={<div className="p-6">Map Page (Coming Soon)</div>} />
                  <Route path="/users" element={<div className="p-6">Users Page (Coming Soon)</div>} />
                  <Route path="/settings" element={<div className="p-6">Settings Page (Coming Soon)</div>} />
                </Routes>
              </AnimatePresence>
            </main>
          </div>
        </div>
      </Router>
      
      {/* Toast Notifications */}
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: {
            background: 'rgba(255, 255, 255, 0.95)',
            backdropFilter: 'blur(10px)',
            border: '1px solid rgba(255, 255, 255, 0.2)',
            borderRadius: '12px',
            boxShadow: '0 8px 32px rgba(0, 0, 0, 0.1)',
          },
          success: {
            iconTheme: {
              primary: '#10b981',
              secondary: '#ffffff',
            },
          },
          error: {
            iconTheme: {
              primary: '#ef4444',
              secondary: '#ffffff',
            },
          },
        }}
      />
    </QueryClientProvider>
  );
}

export default App;
