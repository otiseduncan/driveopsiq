import { Link } from 'react-router-dom';

export default function ForgotPassword(): JSX.Element {
  return (
    <div className="relative overflow-hidden px-4 py-16 sm:px-6 lg:px-8 min-h-screen flex items-center justify-center bg-gradient-to-b from-black via-gray-900 to-gray-900">
      <div className="relative z-10 w-full max-w-md rounded-3xl border border-white/10 bg-black/70 p-10 shadow-2xl backdrop-blur text-center">
        <h1 className="text-2xl font-bold text-white tracking-wide mb-4">Forgot Password</h1>
        <p className="text-sm text-gray-400 mb-6">
          Password reset is not yet available in this version.
          Contact your system administrator to reset your credentials.
        </p>
        <Link
          to="/login"
          className="inline-block rounded-md bg-red-600 px-6 py-2 text-sm font-semibold text-white hover:bg-red-700 transition"
        >
          Back to Login
        </Link>
      </div>
    </div>
  );
}
