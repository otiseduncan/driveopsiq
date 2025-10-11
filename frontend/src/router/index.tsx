import { lazy } from 'react';
import { createBrowserRouter, RouteObject } from 'react-router-dom';

// Layout components (loaded eagerly)
import RootLayout from '@/components/layouts/RootLayout';
import ErrorBoundary from '@/components/ErrorBoundary';

// Lazy-loaded page components for optimal performance
const Dashboard = lazy(() => import('@/pages/Dashboard'));
const Login = lazy(() => import('@/pages/auth/Login'));
const Register = lazy(() => import('@/pages/auth/Register'));
const Profile = lazy(() => import('@/pages/user/Profile'));
const Settings = lazy(() => import('@/pages/user/Settings'));
const APIDocumentation = lazy(() => import('@/pages/docs/APIDocumentation'));
const NotFound = lazy(() => import('@/pages/NotFound'));

// Admin pages (separate chunk for role-based access)
const AdminDashboard = lazy(() => import('@/pages/admin/AdminDashboard'));
const UserManagement = lazy(() => import('@/pages/admin/UserManagement'));
const SystemMetrics = lazy(() => import('@/pages/admin/SystemMetrics'));

// AI features (separate chunk for optional features)
const AIChat = lazy(() => import('@/pages/ai/AIChat'));
const AIAnalytics = lazy(() => import('@/pages/ai/AIAnalytics'));

/**
 * Application router configuration with lazy loading and code splitting.
 * Each route is split into separate chunks for optimal loading performance.
 */
export const router = createBrowserRouter([
  {
    path: '/',
    element: <RootLayout />,
    errorElement: <ErrorBoundary />,
    children: [
      {
        index: true,
        element: <Dashboard />,
        handle: {
          crumb: () => 'Dashboard',
        },
      },
      // Authentication routes
      {
        path: 'auth',
        children: [
          {
            path: 'login',
            element: <Login />,
            handle: {
              crumb: () => 'Login',
            },
          },
          {
            path: 'register', 
            element: <Register />,
            handle: {
              crumb: () => 'Register',
            },
          },
        ],
      },
      // User routes
      {
        path: 'user',
        children: [
          {
            path: 'profile',
            element: <Profile />,
            handle: {
              crumb: () => 'Profile',
            },
          },
          {
            path: 'settings',
            element: <Settings />,
            handle: {
              crumb: () => 'Settings',
            },
          },
        ],
      },
      // Admin routes (protected)
      {
        path: 'admin',
        children: [
          {
            index: true,
            element: <AdminDashboard />,
            handle: {
              crumb: () => 'Admin Dashboard',
            },
          },
          {
            path: 'users',
            element: <UserManagement />,
            handle: {
              crumb: () => 'User Management',
            },
          },
          {
            path: 'metrics',
            element: <SystemMetrics />,
            handle: {
              crumb: () => 'System Metrics',
            },
          },
        ],
      },
      // AI features
      {
        path: 'ai',
        children: [
          {
            path: 'chat',
            element: <AIChat />,
            handle: {
              crumb: () => 'AI Chat',
            },
          },
          {
            path: 'analytics',
            element: <AIAnalytics />,
            handle: {
              crumb: () => 'AI Analytics',
            },
          },
        ],
      },
      // Documentation
      {
        path: 'docs',
        element: <APIDocumentation />,
        handle: {
          crumb: () => 'API Documentation',
        },
      },
      // Catch-all route for 404
      {
        path: '*',
        element: <NotFound />,
      },
    ],
  },
]);

/**
 * Route preloading utilities for improved UX
 */
export const preloadRoute = (routePath: string): Promise<void> => {
  const routeMap: Record<string, () => Promise<any>> = {
    '/': () => import('@/pages/Dashboard'),
    '/auth/login': () => import('@/pages/auth/Login'),
    '/auth/register': () => import('@/pages/auth/Register'), 
    '/user/profile': () => import('@/pages/user/Profile'),
    '/user/settings': () => import('@/pages/user/Settings'),
    '/admin': () => import('@/pages/admin/AdminDashboard'),
    '/admin/users': () => import('@/pages/admin/UserManagement'),
    '/admin/metrics': () => import('@/pages/admin/SystemMetrics'),
    '/ai/chat': () => import('@/pages/ai/AIChat'),
    '/ai/analytics': () => import('@/pages/ai/AIAnalytics'),
    '/docs': () => import('@/pages/docs/APIDocumentation'),
  };

  const loader = routeMap[routePath];
  if (loader) {
    return loader().then(() => {});
  }
  
  return Promise.resolve();
};

/**
 * Preload critical routes for better performance
 */
export const preloadCriticalRoutes = (): void => {
  // Preload most commonly accessed routes
  const criticalRoutes = ['/', '/auth/login', '/user/profile'];
  
  // Use requestIdleCallback for non-blocking preloading
  if ('requestIdleCallback' in window) {
    window.requestIdleCallback(() => {
      criticalRoutes.forEach(route => {
        preloadRoute(route).catch(console.warn);
      });
    });
  } else {
    // Fallback for browsers without requestIdleCallback
    setTimeout(() => {
      criticalRoutes.forEach(route => {
        preloadRoute(route).catch(console.warn);
      });
    }, 2000);
  }
};

export default router;