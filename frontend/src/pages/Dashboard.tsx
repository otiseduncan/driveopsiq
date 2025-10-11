import React, { useState, useEffect } from 'react';

interface ApiHealthResponse {
  status: 'healthy' | 'unhealthy';
  version: string;
  uptime: number;
  timestamp: number;
}

/**
 * Dashboard page component with API health monitoring
 */
const Dashboard: React.FC = () => {
  const [count, setCount] = useState<number>(0);
  const [healthStatus, setHealthStatus] = useState<ApiHealthResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    checkApiHealth();
  }, []);

  const checkApiHealth = async (): Promise<void> => {
    try {
      setIsLoading(true);
      setError(null);
      
      const response = await fetch('/api/v1/health', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`API health check failed: ${response.status}`);
      }

      const health: ApiHealthResponse = await response.json();
      setHealthStatus(health);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCountIncrement = (): void => {
    setCount(prevCount => prevCount + 1);
  };

  const renderHealthStatus = (): React.ReactElement => {
    if (isLoading) {
      return (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-center">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
            <span className="ml-2 text-blue-700">Checking API health...</span>
          </div>
        </div>
      );
    }

    if (error) {
      return (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <h3 className="text-red-800 font-medium">API Error</h3>
          <p className="text-red-700 mt-1">{error}</p>
        </div>
      );
    }

    if (healthStatus) {
      const isHealthy = healthStatus.status === 'healthy';
      return (
        <div className={`border rounded-lg p-4 ${
          isHealthy 
            ? 'bg-green-50 border-green-200' 
            : 'bg-red-50 border-red-200'
        }`}>
          <h3 className={`font-medium ${
            isHealthy ? 'text-green-800' : 'text-red-800'
          }`}>
            API Status: {healthStatus.status}
          </h3>
          <div className={`mt-2 space-y-1 text-sm ${
            isHealthy ? 'text-green-700' : 'text-red-700'
          }`}>
            <p>Version: {healthStatus.version}</p>
            <p>
              Uptime: {Math.floor(healthStatus.uptime / 3600)}h{' '}
              {Math.floor((healthStatus.uptime % 3600) / 60)}m
            </p>
          </div>
        </div>
      );
    }

    return (
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
        <span className="text-gray-600">No health data available</span>
      </div>
    );
  };

  return (
    <div className="space-y-6">
      <div className="bg-white shadow rounded-lg p-6">
        <h1 className="text-2xl font-bold text-gray-900 mb-4">
          SyferStack Dashboard
        </h1>
        
        {renderHealthStatus()}
        
        <div className="mt-6 bg-gray-50 rounded-lg p-4">
          <div className="text-center">
            <button 
              onClick={handleCountIncrement}
              type="button"
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              aria-label="Increment counter"
            >
              Count is {count}
            </button>
            <p className="mt-2 text-sm text-gray-600">
              Click the button to test component reactivity
            </p>
          </div>
        </div>
        
        <div className="mt-6 flex justify-center">
          <button 
            onClick={checkApiHealth}
            disabled={isLoading}
            type="button"
            className="inline-flex items-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
          >
            {isLoading ? 'Checking...' : 'Refresh API Status'}
          </button>
        </div>
      </div>
      
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-lg font-medium text-gray-900 mb-4">
          Quick Stats
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-blue-50 rounded-lg p-4">
            <div className="text-2xl font-bold text-blue-600">{count}</div>
            <div className="text-sm text-blue-700">Button Clicks</div>
          </div>
          <div className="bg-green-50 rounded-lg p-4">
            <div className="text-2xl font-bold text-green-600">
              {healthStatus?.status === 'healthy' ? '✓' : '✗'}
            </div>
            <div className="text-sm text-green-700">API Health</div>
          </div>
          <div className="bg-purple-50 rounded-lg p-4">
            <div className="text-2xl font-bold text-purple-600">V2.0</div>
            <div className="text-sm text-purple-700">Version</div>
          </div>
        </div>
      </div>
      
      <div className="bg-white shadow rounded-lg p-6">
        <p className="text-center text-gray-600">
          🚀 SyferStack V2 - Production-ready full-stack application with enhanced performance
        </p>
      </div>
    </div>
  );
};

export default Dashboard;