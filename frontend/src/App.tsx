import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useState } from 'react'
import Navbar from './components/Navbar'
import Dashboard from './pages/Dashboard'
import TendersList from './pages/TendersList'
import Auth from './pages/Auth'
import './App.css'

// Create a client
const queryClient = new QueryClient()

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false)

  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
          {isAuthenticated && <Navbar />}
          <main className="container mx-auto px-4 py-8">
            <Routes>
              <Route 
                path="/" 
                element={
                  isAuthenticated ? <Dashboard /> : <Auth onAuth={() => setIsAuthenticated(true)} />
                } 
              />
              <Route 
                path="/tenders" 
                element={
                  isAuthenticated ? <TendersList /> : <Auth onAuth={() => setIsAuthenticated(true)} />
                } 
              />
              <Route 
                path="/auth" 
                element={<Auth onAuth={() => setIsAuthenticated(true)} />} 
              />
            </Routes>
          </main>
        </div>
      </Router>
    </QueryClientProvider>
  )
}

export default App
