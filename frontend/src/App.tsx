import React, { Suspense } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, Link, useLocation } from 'react-router-dom';
import './App.css';

// Import components
import LoadingSpinner from '@/components/ui/LoadingSpinner';

// Lazy load pages for better performance and code splitting
const Dashboard = React.lazy(() => import('@/pages/Dashboard'));
const Login = React.lazy(() => import('@/pages/auth/Login'));
const Register = React.lazy(() => import('@/pages/auth/Register'));
const NotFound = React.lazy(() => import('@/pages/NotFound'));

/**
 * Navigation component that uses router location
 */
const Navigation: React.FC = () => {
  const location = useLocation();
  
  const isActive = (path: string) => {
    return location.pathname === path;
  };

  return (
    <nav className="flex items-center space-x-4">
      <Link
        to="/dashboard"
        className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
          isActive('/dashboard')
            ? 'bg-blue-100 text-blue-700'
            : 'text-gray-600 hover:text-gray-900'
        }`}
      >
        Dashboard
      </Link>
      <Link
        to="/login"
        className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
          isActive('/login')
            ? 'bg-blue-100 text-blue-700'
            : 'text-gray-600 hover:text-gray-900'
        }`}
      >
        Login
      </Link>
      <Link
        to="/register"
        className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
          isActive('/register')
            ? 'bg-blue-100 text-blue-700'
            : 'text-gray-600 hover:text-gray-900'
        }`}
      >
        Register
      </Link>
      <span className="text-sm text-gray-500">
        🚀 Performance Optimized • 📦 Code Split • ⚡ Lazy Loaded
      </span>
    </nav>
  );
};

/**
 * Enhanced App component with React Router, lazy loading, and performance optimizations.
 * Features:
 * - Code splitting with React.lazy()
 * - Suspense boundaries for smooth loading states
 * - React Router for proper navigation
 * - Performance-optimized component structure
 * - SEO-friendly routing
 */
const App: React.FC = () => {
  return (
    <Router>
      <div className="min-h-screen bg-gray-50 flex flex-col">
        {/* Header with Navigation */}
        <header className="bg-white shadow-sm border-b">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between h-16">
              <div className="flex items-center">
                <Link to="/" className="text-xl font-semibold text-gray-900 hover:text-gray-700">
                  SyferStack V2
                </Link>
              </div>
              <Navigation />
            </div>
          </div>
        </header>
        
        {/* Main content with routing and Suspense */}
        <main className="flex-1 max-w-7xl mx-auto w-full py-6 sm:px-6 lg:px-8">
          <Suspense 
            fallback={
              <div className="flex justify-center items-center h-64">
                <LoadingSpinner />
              </div>
            }
          >
            <Routes>
              {/* Public Routes */}
              <Route path="/login" element={<Login />} />
              <Route path="/register" element={<Register />} />
              
              {/* Protected Routes */}
              <Route path="/dashboard" element={<Dashboard />} />
              
              {/* Default and Fallback Routes */}
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
              <Route path="/404" element={<NotFound />} />
              <Route path="*" element={<Navigate to="/404" replace />} />
            </Routes>
          </Suspense>
        </main>
        
        {/* Footer */}
        <footer className="bg-white border-t mt-auto">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
            <div className="text-center text-sm text-gray-600 space-y-2">
              <p>© 2025 SyferStack. All rights reserved.</p>
              <p className="text-xs">
                ⚡ Optimized build with Vite • 📦 Code splitting enabled • 🎯 Lazy loading active
              </p>
            </div>
          </div>
        </footer>
      </div>
    </Router>
  );
};

export default App;