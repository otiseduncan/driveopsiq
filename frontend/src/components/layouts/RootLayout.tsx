import React, { Suspense } from 'react';
import { Outlet } from 'react-router-dom';
import LoadingSpinner from '@/components/ui/LoadingSpinner';

/**
 * Root layout component that wraps all pages.
 * Provides consistent layout structure and loading states.
 */
const RootLayout: React.FC = () => {
  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <h1 className="text-xl font-semibold text-gray-900">
                SyferStack V2
              </h1>
            </div>
            <nav className="flex items-center space-x-4">
              {/* Navigation will be enhanced later */}
              <span className="text-sm text-gray-600">Navigation</span>
            </nav>
          </div>
        </div>
      </header>
      
      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <Suspense 
          fallback={
            <div className="flex justify-center items-center h-64">
              <LoadingSpinner />
            </div>
          }
        >
          <Outlet />
        </Suspense>
      </main>
      
      <footer className="bg-white border-t mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <p className="text-center text-sm text-gray-600">
            © 2025 SyferStack. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  );
};

export default RootLayout;