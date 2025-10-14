import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router-dom';

import { AuthService } from '@/services/api';
import { UserCreate } from '@/types';

export default function Register(): JSX.Element {
  const navigate = useNavigate();
  const [formData, setFormData] = useState<UserCreate>({
    email: '',
    full_name: '',
    password: '',
  });
  const [error, setError] = useState<string | null>(null);

  const registerMutation = useMutation({
    mutationFn: async (payload: UserCreate) => {
      await AuthService.register(payload);
      await AuthService.login({ email: payload.email, password: payload.password });
    },
    onSuccess: () => {
      setError(null);
      navigate('/driveops', { replace: true });
    },
    onError: (mutationError: unknown) => {
      const message = mutationError instanceof Error ? mutationError.message : 'Registration failed.';
      setError(message);
    },
  });

  const handleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = event.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    registerMutation.mutate(formData);
  };

  return (
    <div className="relative overflow-hidden px-4 py-16 sm:px-6 lg:px-8 min-h-screen flex items-center justify-center bg-gradient-to-b from-black via-gray-900 to-gray-900">
      <div className="pointer-events-none absolute inset-0 bg-driveops-grid opacity-20" aria-hidden="true" />
      <div
        className="pointer-events-none absolute inset-0 bg-center bg-contain bg-no-repeat opacity-10"
        style={{ backgroundImage: "url('/assets/driveops-logo.png')" }}
        aria-hidden="true"
      />

      <div className="relative z-10 w-full max-w-md rounded-3xl border border-white/10 bg-black/70 p-10 shadow-2xl backdrop-blur">
        <header className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-white tracking-wide">Create DriveOps Account</h1>
          <p className="mt-2 text-sm text-gray-400">Secure onboarding for DriveOps IQ calibration teams</p>
        </header>

        {error ? (
          <div className="mb-4 rounded-md border border-red-500/40 bg-red-500/10 px-4 py-2 text-sm text-red-200">
            {error}
          </div>
        ) : null}

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label htmlFor="full_name" className="mb-1 block text-xs font-semibold uppercase tracking-wide text-gray-300">
              Full Name
            </label>
            <input
              id="full_name"
              name="full_name"
              type="text"
              required
              value={formData.full_name}
              onChange={handleChange}
              className="w-full rounded-md border border-white/10 bg-gray-900/80 px-4 py-3 text-gray-100 placeholder-gray-500 focus:border-driveops-red focus:outline-none focus:ring-2 focus:ring-driveops-red/70"
              placeholder="Enter your name"
            />
          </div>

          <div>
            <label htmlFor="email" className="mb-1 block text-xs font-semibold uppercase tracking-wide text-gray-300">
              Email
            </label>
            <input
              id="email"
              name="email"
              type="email"
              autoComplete="email"
              required
              value={formData.email}
              onChange={handleChange}
              className="w-full rounded-md border border-white/10 bg-gray-900/80 px-4 py-3 text-gray-100 placeholder-gray-500 focus:border-driveops-red focus:outline-none focus:ring-2 focus:ring-driveops-red/70"
              placeholder="you@driveops.com"
            />
          </div>

          <div>
            <label htmlFor="password" className="mb-1 block text-xs font-semibold uppercase tracking-wide text-gray-300">
              Password
            </label>
            <input
              id="password"
              name="password"
              type="password"
              autoComplete="new-password"
              required
              value={formData.password}
              onChange={handleChange}
              className="w-full rounded-md border border-white/10 bg-gray-900/80 px-4 py-3 text-gray-100 placeholder-gray-500 focus:border-driveops-red focus:outline-none focus:ring-2 focus:ring-driveops-red/70"
              placeholder="Create a strong password"
            />
            <p className="mt-2 text-xs text-gray-400">
              Use at least 8 characters with uppercase, lowercase, numeric, and special characters.
            </p>
          </div>

          <button
            type="submit"
            disabled={registerMutation.isPending}
            className="w-full rounded-md bg-driveops-red px-4 py-3 text-sm font-semibold uppercase tracking-wide text-white transition duration-300 hover:bg-red-500 focus:outline-none focus:ring-2 focus:ring-driveops-red/70 disabled:cursor-not-allowed disabled:opacity-70"
          >
            {registerMutation.isPending ? 'Creating account…' : 'Register'}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-gray-400">
          Already have an account?{' '}
          <Link to="/login" className="font-medium text-gray-200 underline-offset-4 hover:text-white hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
