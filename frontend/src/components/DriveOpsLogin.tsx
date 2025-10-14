import React, { useState } from 'react';
import DriveOpsRequestForm from '@/modules/driveops_iq/DriveOpsRequestForm';

const DriveOpsLogin: React.FC = () => {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [credentials, setCredentials] = useState({
    email: '',
    password: ''
  });

  // Ensure full viewport control
  React.useEffect(() => {
    document.body.style.margin = '0';
    document.body.style.padding = '0';
    document.body.style.overflow = 'auto';
    return () => {
      document.body.style.margin = '';
      document.body.style.padding = '';
      document.body.style.overflow = '';
    };
  }, []);

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    // Simple demo login - in production this would validate against the backend
    if (credentials.email && credentials.password) {
      setIsLoggedIn(true);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setCredentials(prev => ({
      ...prev,
      [name]: value
    }));
  };

  if (isLoggedIn) {
    return (
      <div className="fixed inset-0 min-h-screen bg-gradient-to-br from-blue-900 via-blue-800 to-indigo-900 overflow-auto">
        {/* Header */}
        <header className="bg-white/10 backdrop-blur-sm border-b border-white/20">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center h-16">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 bg-white rounded-lg flex items-center justify-center">
                  <span className="text-blue-600 font-bold text-xl">D</span>
                </div>
                <h1 className="text-2xl font-bold text-white">DriveOps IQ</h1>
              </div>
              <button
                onClick={() => setIsLoggedIn(false)}
                className="text-white/80 hover:text-white transition-colors px-4 py-2 rounded-md hover:bg-white/10"
              >
                Logout
              </button>
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <DriveOpsRequestForm />
        </main>

        {/* Footer */}
        <footer className="bg-white/5 backdrop-blur-sm border-t border-white/10 mt-12">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
            <div className="text-center text-white/60">
              <p>© 2025 DriveOps IQ. Advanced Driver Assistance Systems Calibration Platform.</p>
            </div>
          </div>
        </footer>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 min-h-screen bg-gradient-to-br from-blue-900 via-blue-800 to-indigo-900 flex flex-col justify-center overflow-auto">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        {/* Logo and Brand */}
        <div className="flex justify-center mb-8">
          <div className="w-20 h-20 bg-white rounded-2xl flex items-center justify-center shadow-2xl">
            <span className="text-blue-600 font-bold text-3xl">D</span>
          </div>
        </div>
        
        <h1 className="text-center text-4xl font-bold text-white mb-2">
          DriveOps IQ
        </h1>
        <p className="text-center text-xl text-blue-100 mb-8">
          Advanced Driver Assistance Systems
        </p>
        <p className="text-center text-lg text-blue-200 mb-12">
          Calibration Management Platform
        </p>
      </div>

      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white/10 backdrop-blur-lg py-8 px-6 shadow-2xl rounded-2xl border border-white/20">
          <form className="space-y-6" onSubmit={handleLogin}>
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-white mb-2">
                Email address
              </label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                required
                value={credentials.email}
                onChange={handleInputChange}
                className="w-full px-3 py-3 bg-white/20 border border-white/30 rounded-lg text-white placeholder-white/60 focus:outline-none focus:ring-2 focus:ring-blue-400 focus:border-transparent backdrop-blur-sm"
                placeholder="Enter your email"
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-white mb-2">
                Password
              </label>
              <input
                id="password"
                name="password"
                type="password"
                autoComplete="current-password"
                required
                value={credentials.password}
                onChange={handleInputChange}
                className="w-full px-3 py-3 bg-white/20 border border-white/30 rounded-lg text-white placeholder-white/60 focus:outline-none focus:ring-2 focus:ring-blue-400 focus:border-transparent backdrop-blur-sm"
                placeholder="Enter your password"
              />
            </div>

            <div>
              <button
                type="submit"
                className="w-full flex justify-center py-3 px-4 border border-transparent rounded-lg shadow-lg text-sm font-medium text-blue-900 bg-white hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-all duration-200 transform hover:scale-105"
              >
                Sign in to DriveOps IQ
              </button>
            </div>
          </form>

          <div className="mt-6">
            <div className="text-center">
              <p className="text-sm text-white/60">
                Demo credentials: any email and password combination will work
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="sm:mx-auto sm:w-full sm:max-w-2xl mt-8">
        <div className="text-center text-white/80">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-8">
            <div className="text-center">
              <div className="w-12 h-12 bg-white/20 rounded-xl mx-auto mb-3 flex items-center justify-center">
                <span className="text-white text-2xl">🎯</span>
              </div>
              <h3 className="text-sm font-semibold">Precise Calibration</h3>
              <p className="text-xs text-white/60 mt-1">Advanced ADAS calibration technology</p>
            </div>
            <div className="text-center">
              <div className="w-12 h-12 bg-white/20 rounded-xl mx-auto mb-3 flex items-center justify-center">
                <span className="text-white text-2xl">⚡</span>
              </div>
              <h3 className="text-sm font-semibold">Fast Processing</h3>
              <p className="text-xs text-white/60 mt-1">Quick turnaround times</p>
            </div>
            <div className="text-center">
              <div className="w-12 h-12 bg-white/20 rounded-xl mx-auto mb-3 flex items-center justify-center">
                <span className="text-white text-2xl">🔒</span>
              </div>
              <h3 className="text-sm font-semibold">Secure Platform</h3>
              <p className="text-xs text-white/60 mt-1">Enterprise-grade security</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DriveOpsLogin;