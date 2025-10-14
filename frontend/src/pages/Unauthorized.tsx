import React from 'react';
import { Link } from 'react-router-dom';

const Unauthorized: React.FC = () => (
  <div className="flex min-h-screen flex-col items-center justify-center bg-driveops-slate px-4 text-center text-white">
    <h1 className="text-3xl font-semibold">Access Restricted</h1>
    <p className="mt-3 max-w-md text-sm text-gray-300">
      Your account does not have access to this area. Please sign in with the appropriate DriveOps-IQ role or contact an administrator for assistance.
    </p>
    <div className="mt-6 flex gap-3">
      <Link
        to="/login"
        className="rounded-lg bg-cherryRed px-5 py-2 text-sm font-medium text-white transition hover:bg-red-700"
      >
        Back to Login
      </Link>
      <Link
        to="/"
        className="rounded-lg border border-white/30 px-5 py-2 text-sm font-medium text-white transition hover:bg-white/10"
      >
        Return Home
      </Link>
    </div>
  </div>
);

export default Unauthorized;
