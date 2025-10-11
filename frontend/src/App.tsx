import React, { useState, useEffect } from 'react';
import './App.css';

interface AppState {
  isLoading: boolean;
  error: string | null;
  user: User | null;
}

interface User {
  id: string;
  email: string;
  is_active: boolean;
  created_at: string;
}

interface ApiHealthResponse {
  status: 'healthy' | 'unhealthy';
  version: string;
  uptime: number;
  timestamp: number;
}

const App: React.FC = () => {
  const [count, setCount] = useState<number>(0);
  const [appState, setAppState] = useState<AppState>({
    isLoading: false,
    error: null,
    user: null,
  });
  const [healthStatus, setHealthStatus] = useState<ApiHealthResponse | null>(null);

  useEffect(() => {
    checkApiHealth();
  }, []);

  const checkApiHealth = async (): Promise<void> => {
    try {
      setAppState(prev => ({ ...prev, isLoading: true, error: null }));
      
      const response = await fetch('/api/health', {
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
      setAppState(prev => ({ ...prev, error: errorMessage }));
    } finally {
      setAppState(prev => ({ ...prev, isLoading: false }));
    }
  };

  const handleCountIncrement = (): void => {
    setCount(prevCount => prevCount + 1);
  };

  const renderHealthStatus = (): React.ReactElement => {
    if (appState.isLoading) {
      return <div className="health-status loading">Checking API health...</div>;
    }

    if (appState.error) {
      return <div className="health-status error">API Error: {appState.error}</div>;
    }

    if (healthStatus) {
      return (
        <div className={`health-status ${healthStatus.status}`}>
          <h3>API Status: {healthStatus.status}</h3>
          <p>Version: {healthStatus.version}</p>
          <p>Uptime: {Math.floor(healthStatus.uptime / 3600)}h {Math.floor((healthStatus.uptime % 3600) / 60)}m</p>
        </div>
      );
    }

    return <div className="health-status">No health data available</div>;
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>SyferStack Frontend</h1>
        
        {renderHealthStatus()}
        
        <div className="card">
          <button 
            onClick={handleCountIncrement}
            type="button"
            aria-label="Increment counter"
          >
            count is {count}
          </button>
          <p>
            Edit <code>src/App.tsx</code> and save to test HMR
          </p>
        </div>
        
        <div className="actions">
          <button 
            onClick={checkApiHealth}
            disabled={appState.isLoading}
            type="button"
          >
            {appState.isLoading ? 'Checking...' : 'Refresh API Status'}
          </button>
        </div>
        
        <p className="read-the-docs">
          SyferStack V2 - Production-ready full-stack application
        </p>
      </header>
    </div>
  );
};

export default App;