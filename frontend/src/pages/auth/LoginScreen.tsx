import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import type { LoginRequest, LoginResponse } from '@/types';

export default function LoginScreen(): JSX.Element {
  const navigate = useNavigate();
  const [fadeClass, setFadeClass] = useState('opacity-0');
  const [formData, setFormData] = useState<LoginRequest>({ email: '', password: '' });
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    const fadeTimer = window.setTimeout(() => setFadeClass('opacity-100'), 150);
    return () => {
      window.clearTimeout(fadeTimer);
      setFadeClass('opacity-0');
    };
  }, []);

  const splashClasses = useMemo(
    () =>
      `relative overflow-hidden px-4 py-16 sm:px-6 lg:px-8 min-h-screen flex items-center justify-center bg-gradient-to-b from-black via-gray-900 to-gray-900 transition-opacity duration-700 ${fadeClass}`,
    [fadeClass],
  );

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);

    try {
      const apiBaseUrl =
        import.meta.env.VITE_API_BASE_URL ?? import.meta.env.VITE_API_URL ?? '';

      if (!apiBaseUrl) {
        throw new Error('API base URL is not configured.');
      }

      const response = await fetch(`${apiBaseUrl}/api/v1/auth/login/json`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      });

      if (!response.ok) {
        throw new Error('Login failed');
      }

      const data = (await response.json()) as LoginResponse;
      const roleCandidates = [
        data.role ?? null,
        ...(data.user?.roles
          ?.split(',')
          .map((role) => role.trim())
          .filter(Boolean) ?? []),
      ].filter((role): role is string => Boolean(role && role.length));
      const primaryRole = roleCandidates.length > 0 ? roleCandidates[0] : null;

      localStorage.setItem('token', data.access_token);
      localStorage.setItem('refreshToken', data.refresh_token);

      if (primaryRole) {
        localStorage.setItem('role', primaryRole);
      } else {
        localStorage.removeItem('role');
      }

      // Store user data for potential use in UI
      if (data.user) {
        localStorage.setItem('currentUser', JSON.stringify(data.user));
      }

      switch (primaryRole) {
        case 'admin':
        case 'super_admin':
          navigate('/dashboard/admin', { replace: true });
          break;
        case 'manager_field':
          navigate('/dashboard/manager/field', { replace: true });
          break;
        case 'manager_shop':
          navigate('/dashboard/manager/shop', { replace: true });
          break;
        case 'cmr_shop':
          navigate('/dashboard/cmr/shop', { replace: true });
          break;
        case 'cmr_mobile':
          navigate('/dashboard/cmr/mobile', { replace: true });
          break;
        case 'technician':
          navigate('/dashboard/technician', { replace: true });
          break;
        default:
          navigate('/unauthorized', { replace: true });
      }
    } catch {
      localStorage.removeItem('token');
      localStorage.removeItem('refreshToken');
      localStorage.removeItem('role');
      localStorage.removeItem('currentUser');
      setError('Invalid credentials or server unreachable.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className={splashClasses}>
      <div className="pointer-events-none absolute inset-0 bg-driveops-grid opacity-20" aria-hidden="true" />
      <div
        className="pointer-events-none absolute inset-0 bg-center bg-contain bg-no-repeat opacity-10"
        style={{ backgroundImage: "url('/assets/driveops-logo.png')" }}
        aria-hidden="true"
      />

      <div className="relative z-10 w-full max-w-md rounded-3xl border border-white/10 bg-black/70 p-10 shadow-2xl backdrop-blur">
        <header className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-white tracking-wide">DriveOps-IQ Login</h1>
          <p className="mt-2 text-sm text-gray-400">
            Secure access for technicians, CMR, managers, and administrators
          </p>
        </header>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label htmlFor="email" className="sr-only">
              Email
            </label>
            <input
              id="email"
              name="email"
              type="email"
              autoComplete="email"
              value={formData.email}
              onChange={(event) =>
                setFormData((prev) => ({ ...prev, email: event.target.value }))
              }
              required
              className="w-full rounded-md border border-gray-700 bg-gray-900/80 px-4 py-3 text-gray-100 placeholder-gray-500 focus:border-red-500 focus:outline-none focus:ring-2 focus:ring-red-500/70"
              placeholder="Email"
            />
          </div>

          <div>
            <label htmlFor="password" className="sr-only">
              Password
            </label>
            <input
              id="password"
              name="password"
              type="password"
              autoComplete="current-password"
              value={formData.password}
              onChange={(event) =>
                setFormData((prev) => ({ ...prev, password: event.target.value }))
              }
              required
              className="w-full rounded-md border border-gray-700 bg-gray-900/80 px-4 py-3 text-gray-100 placeholder-gray-500 focus:border-red-500 focus:outline-none focus:ring-2 focus:ring-red-500/70"
              placeholder="Password"
            />
          </div>

          {error ? (
            <p className="rounded-md border border-red-500/40 bg-red-500/10 px-4 py-2 text-sm text-red-200">
              {error}
            </p>
          ) : null}

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full rounded-md bg-red-600 py-3 text-sm font-semibold uppercase tracking-wide text-white transition duration-300 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-400 disabled:cursor-not-allowed disabled:opacity-70"
          >
            {isSubmitting ? 'Signing In…' : 'Sign In'}
          </button>
        </form>

        <div className="mt-6 flex items-center justify-between text-sm text-gray-400">
          <Link to="/register" className="text-gray-300 transition hover:text-white">
            Create account
          </Link>
          <Link to="/forgot-password" className="text-gray-300 transition hover:text-white">
            Forgot password?
          </Link>
        </div>
      </div>
    </div>
  );
}
