import React from 'react';

/**
 * Simple loading spinner component for lazy-loaded content
 */
const LoadingSpinner: React.FC = () => {
  return (
    <div className="flex items-center justify-center">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      <span className="ml-2 text-sm text-gray-600">Loading...</span>
    </div>
  );
};

export default LoadingSpinner;