import { lazy, Suspense } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import './App.css';

import LoadingSpinner from '@/components/ui/LoadingSpinner';
import SplashScreen from '@/components/SplashScreen';
import LoginScreen from '@/components/LoginScreen';
import Dashboard from '@/components/Dashboard';
import { DriveOpsRequestForm } from '@/modules/driveops_iq';
import AdminDashboard from '@/pages/admin/AdminDashboard';
import ManagerRouter from './router/ManagerRouter';
const Register = lazy(() => import('@/pages/auth/Register'));
const ForgotPassword = lazy(() => import('@/pages/auth/ForgotPassword'));
const NotFound = lazy(() => import('@/pages/NotFound'));
const Unauthorized = lazy(() => import('@/pages/Unauthorized'));
const ShopCMRDashboard = lazy(() => import('@/pages/cmr/ShopCMRDashboard'));
const MobileCMRDashboard = lazy(() => import('@/pages/cmr/MobileCMRDashboard'));
const TechnicianDashboard = lazy(() => import('@/pages/technician/TechnicianDashboard'));

const RequireAuth: React.FC<{ children: JSX.Element }> = ({ children }) => {
  if (typeof window === 'undefined') {
    return children;
  }

  const token = window.localStorage.getItem('token');
  if (!token) {
    return <Navigate to="/login" replace />;
  }

  return children;
};

const App: React.FC = () => (
  <Router>
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center bg-driveops-slate">
          <LoadingSpinner />
        </div>
      }
    >
      <Routes>
        <Route path="/" element={<SplashScreen />} />
        <Route path="/login" element={<LoginScreen />} />
        <Route path="/register" element={<Register />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route
          path="/driveops"
          element={
            <RequireAuth>
              <DriveOpsRequestForm />
            </RequireAuth>
          }
        />
        <Route
          path="/dashboard"
          element={
            <RequireAuth>
              <Dashboard />
            </RequireAuth>
          }
        />
        <Route
          path="/dashboard/admin"
          element={
            <RequireAuth>
              <AdminDashboard />
            </RequireAuth>
          }
        />
        <Route
          path="/dashboard/cmr/shop"
          element={
            <RequireAuth>
              <ShopCMRDashboard />
            </RequireAuth>
          }
        />
        <Route
          path="/dashboard/cmr/mobile"
          element={
            <RequireAuth>
              <MobileCMRDashboard />
            </RequireAuth>
          }
        />
        <Route
          path="/dashboard/technician"
          element={
            <RequireAuth>
              <TechnicianDashboard />
            </RequireAuth>
          }
        />
        <Route
          path="/dashboard/manager/*"
          element={
            <RequireAuth>
              <ManagerRouter />
            </RequireAuth>
          }
        />
        <Route path="/unauthorized" element={<Unauthorized />} />
        <Route path="/404" element={<NotFound />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  </Router>
);

export default App;
