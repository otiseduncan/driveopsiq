import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import {
  LayoutDashboard,
  Users,
  Wrench,
  BarChart3,
  Settings,
  RefreshCw,
  LogOut,
  Search,
  type LucideIcon,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';

type SummaryStats = {
  users: number;
  shops: number;
  requests: number;
  revenue: number;
};

type JobStatus = 'Pending' | 'In Progress' | 'Completed' | 'On Hold' | 'Cancelled' | string;

type JobPoolItem = {
  id: string;
  vin: string;
  vehicle: string;
  technician: string;
  status: JobStatus;
  shop: string;
};

const DEFAULT_STATS: SummaryStats = {
  users: 18,
  shops: 9,
  requests: 34,
  revenue: 15200,
};

const DEFAULT_JOB_POOL: JobPoolItem[] = [
  {
    id: 'RO-2301',
    vin: '1HGCM82633A004352',
    vehicle: 'Honda Accord 2023',
    technician: 'John Smith',
    status: 'In Progress',
    shop: 'Precision Auto Cal',
  },
  {
    id: 'RO-2302',
    vin: '5YJ3E1EA8LF673122',
    vehicle: 'Tesla Model 3',
    technician: 'Jane Doe',
    status: 'Pending',
    shop: 'DriveCal North',
  },
  {
    id: 'RO-2303',
    vin: '1FTFW1E89NFC09211',
    vehicle: 'Ford F-150',
    technician: 'Marcus Lee',
    status: 'Completed',
    shop: 'MAS East',
  },
];

const normaliseJob = (job: Partial<JobPoolItem>): JobPoolItem => ({
  id: job.id ?? 'RO-UNKNOWN',
  vin: job.vin ?? 'N/A',
  vehicle: job.vehicle ?? 'Vehicle Pending',
  technician: job.technician ?? 'Unassigned',
  status: job.status ?? 'Pending',
  shop: job.shop ?? 'Unassigned',
});

const NAV_LINKS: Array<{ label: string; icon: LucideIcon }> = [
  { label: 'Dashboard', icon: LayoutDashboard },
  { label: 'Users', icon: Users },
  { label: 'Job Pool', icon: Wrench },
  { label: 'Analytics', icon: BarChart3 },
  { label: 'Settings', icon: Settings },
];

const AdminDashboard: React.FC = () => {
  const [stats, setStats] = useState<SummaryStats>(DEFAULT_STATS);
  const [jobPool, setJobPool] = useState<JobPoolItem[]>(DEFAULT_JOB_POOL);
  const [loading, setLoading] = useState<boolean>(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [lastSynced, setLastSynced] = useState<Date | null>(null);
  const navigate = useNavigate();

  const fetchDashboardData = useCallback(
    async (signal?: AbortSignal) => {
      if (typeof window === 'undefined') {
        return;
      }

      setLoading(true);
      const token = window.localStorage.getItem('token');
      const baseUrl = import.meta.env.VITE_API_BASE_URL;

      if (!baseUrl) {
        // Fallback to placeholder data when API base URL is not configured yet
        setStats(DEFAULT_STATS);
        setJobPool(DEFAULT_JOB_POOL);
        setLastSynced(new Date());
        setLoading(false);
        return;
      }

      const requestInit: RequestInit = {
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
        signal,
      };

      try {
        const [summaryResponse, jobsResponse] = await Promise.all([
          fetch(`${baseUrl}/api/v1/driveops/summary`, requestInit),
          fetch(`${baseUrl}/api/v1/driveops/requests`, requestInit),
        ]);

        if (!signal?.aborted && summaryResponse.ok) {
          const summary = (await summaryResponse.json()) as Partial<SummaryStats>;
          setStats({
            users: summary.users ?? DEFAULT_STATS.users,
            shops: summary.shops ?? DEFAULT_STATS.shops,
            requests: summary.requests ?? DEFAULT_STATS.requests,
            revenue: summary.revenue ?? DEFAULT_STATS.revenue,
          });
        } else if (!signal?.aborted) {
          setStats(DEFAULT_STATS);
        }

        if (!signal?.aborted && jobsResponse.ok) {
          const jobs = (await jobsResponse.json()) as unknown;
          if (Array.isArray(jobs) && jobs.length > 0) {
            setJobPool(
              jobs.map((job) => normaliseJob((job ?? {}) as Partial<JobPoolItem>))
            );
          } else {
            setJobPool(DEFAULT_JOB_POOL);
          }
        } else if (!signal?.aborted) {
          setJobPool(DEFAULT_JOB_POOL);
        }
      } catch (error) {
        if (!signal?.aborted) {
          setStats(DEFAULT_STATS);
          setJobPool(DEFAULT_JOB_POOL);
        }
      } finally {
        if (!signal?.aborted) {
          setLoading(false);
          setLastSynced(new Date());
        }
      }
    },
    []
  );

  useEffect(() => {
    const controller = new AbortController();
    void fetchDashboardData(controller.signal);

    return () => controller.abort();
  }, [fetchDashboardData]);

  const logout = () => {
    if (typeof window !== 'undefined') {
      window.localStorage.removeItem('token');
      window.localStorage.removeItem('refreshToken');
      window.localStorage.removeItem('role');
      window.localStorage.removeItem('currentUser');
    }
    navigate('/login');
  };

  const filteredJobs = useMemo(() => {
    if (!searchTerm.trim()) {
      return jobPool;
    }

    const lowered = searchTerm.toLowerCase();
    return jobPool.filter((job) =>
      [job.id, job.vehicle, job.vin, job.technician, job.shop].some((value) =>
        value.toLowerCase().includes(lowered)
      )
    );
  }, [jobPool, searchTerm]);

  const getStatusStyles = (status: JobStatus) => {
    const normalisedStatus = status.toLowerCase();
    if (normalisedStatus.includes('complete')) {
      return 'bg-green-700/40 text-green-300';
    }
    if (
      normalisedStatus.includes('progress') ||
      normalisedStatus.includes('active') ||
      normalisedStatus.includes('assigned')
    ) {
      return 'bg-yellow-600/30 text-yellow-200';
    }
    if (normalisedStatus.includes('pending') || normalisedStatus.includes('scheduled')) {
      return 'bg-gray-700/40 text-gray-200';
    }
    if (normalisedStatus.includes('hold')) {
      return 'bg-orange-600/30 text-orange-200';
    }
    if (normalisedStatus.includes('cancel')) {
      return 'bg-red-700/30 text-red-300';
    }
    return 'bg-neutral-700/30 text-neutral-200';
  };

  return (
    <div className="flex min-h-screen flex-col bg-gradient-to-b from-black via-neutral-900 to-zinc-900 text-white">
      <header className="sticky top-0 z-50 border-b border-neutral-800 bg-gradient-to-r from-black via-neutral-900 to-zinc-900/95 backdrop-blur-sm">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2">
              <div className="h-10 w-10 rounded-xl bg-cherryRed/10 ring-1 ring-cherryRed/60" />
              <div>
                <p className="text-xs uppercase tracking-[0.35em] text-gray-400">Unified Control</p>
                <h1 className="text-lg font-semibold text-white">DriveOps-IQ</h1>
              </div>
            </div>
            <nav className="hidden lg:flex items-center gap-4 text-sm text-gray-300">
              {NAV_LINKS.map((link) => (
                <NavButton
                  key={link.label}
                  label={link.label}
                  icon={link.icon}
                  isActive={link.label === 'Job Pool'}
                />
              ))}
            </nav>
          </div>
          <div className="flex items-center gap-3">
            <div className="hidden md:block relative">
              <Search
                size={16}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500"
              />
              <input
                type="search"
                value={searchTerm}
                onChange={(event) => setSearchTerm(event.target.value)}
                placeholder="Search jobs, VINs, technicians..."
                className="w-72 rounded-xl border border-neutral-700 bg-neutral-900/80 py-2 pl-9 pr-4 text-sm text-gray-200 placeholder:text-gray-500 focus:border-cherryRed focus:outline-none focus:ring-2 focus:ring-cherryRed/40"
              />
            </div>
            <button
              onClick={logout}
              className="flex items-center gap-2 rounded-xl border border-neutral-700 bg-neutral-900 px-4 py-2 text-sm text-gray-200 transition hover:border-cherryRed hover:text-white"
            >
              <LogOut size={16} />
              Logout
            </button>
          </div>
        </div>
        <nav className="border-t border-neutral-800 bg-black/40 py-3 lg:hidden">
          <div className="flex items-center gap-2 overflow-x-auto px-4 text-xs text-gray-300">
            {NAV_LINKS.map((link) => (
              <NavButton
                key={link.label}
                label={link.label}
                icon={link.icon}
                isActive={link.label === 'Job Pool'}
                compact
              />
            ))}
          </div>
        </nav>
      </header>

      <main className="flex-1 overflow-y-auto">
        <div className="mx-auto flex max-w-7xl flex-col gap-10 px-4 py-8 sm:px-6 lg:px-8">
          <section className="space-y-4">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <h2 className="text-xl font-semibold text-white">System Overview</h2>
                <p className="text-sm text-gray-400">
                  Real-time vitals across DriveOps-IQ operations.
                </p>
              </div>
              <p className="text-xs uppercase tracking-widest text-gray-500">
                Synced {lastSynced ? lastSynced.toLocaleTimeString() : '—'}
              </p>
            </div>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
              {[
                { label: 'Users', value: stats.users.toLocaleString() },
                { label: 'Shops', value: stats.shops.toLocaleString() },
                { label: 'Requests', value: stats.requests.toLocaleString() },
                {
                  label: 'Revenue',
                  value: `$${stats.revenue.toLocaleString()}`,
                },
              ].map((card) => (
                <motion.div
                  key={card.label}
                  whileHover={{ scale: 1.02 }}
                  className="rounded-3xl border border-neutral-800 bg-neutral-900/60 p-6 shadow-lg shadow-black/40 transition"
                >
                  <p className="text-sm uppercase tracking-wide text-gray-400">{card.label}</p>
                  <p className="mt-2 text-3xl font-bold text-cherryRed">{card.value}</p>
                </motion.div>
              ))}
            </div>
          </section>

          <section className="space-y-4">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 className="text-xl font-semibold text-white">Centralized Job Pool</h2>
                <p className="text-sm text-gray-400">
                  All live repair and calibration requests streaming across the network.
                </p>
              </div>
              <div className="flex w-full flex-col gap-3 sm:w-auto sm:flex-row sm:items-center">
                <div className="relative w-full md:hidden">
                  <Search
                    size={16}
                    className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500"
                  />
                  <input
                    type="search"
                    value={searchTerm}
                    onChange={(event) => setSearchTerm(event.target.value)}
                    placeholder="Search jobs..."
                    className="w-full rounded-xl border border-neutral-700 bg-neutral-900/80 py-2 pl-9 pr-4 text-sm text-gray-200 placeholder:text-gray-500 focus:border-cherryRed focus:outline-none focus:ring-2 focus:ring-cherryRed/40"
                  />
                </div>
                <button
                  onClick={() => void fetchDashboardData()}
                  disabled={loading}
                  className="flex items-center justify-center gap-2 rounded-xl bg-cherryRed px-5 py-2 text-sm font-semibold text-white shadow-lg shadow-cherryRed/30 transition hover:bg-red-700 disabled:cursor-not-allowed disabled:bg-red-800/60"
                >
                  <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
                  {loading ? 'Refreshing' : 'Refresh'}
                </button>
              </div>
            </div>

            <div className="overflow-hidden rounded-3xl border border-neutral-800 bg-neutral-950/60 shadow-xl shadow-black/50">
              <div className="overflow-x-auto">
                <table className="min-w-full table-auto text-left text-sm text-gray-200">
                  <thead className="bg-black/50 text-xs uppercase tracking-wide text-gray-400">
                    <tr>
                      <th className="px-4 py-4 font-medium">RO #</th>
                      <th className="px-4 py-4 font-medium">Vehicle</th>
                      <th className="px-4 py-4 font-medium">VIN</th>
                      <th className="px-4 py-4 font-medium">Technician</th>
                      <th className="px-4 py-4 font-medium">Shop</th>
                      <th className="px-4 py-4 font-medium">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-neutral-800/80">
                    {filteredJobs.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="px-4 py-10 text-center text-gray-500">
                          No jobs match the current filters. Try adjusting your search.
                        </td>
                      </tr>
                    ) : (
                      filteredJobs.map((job) => (
                        <tr
                          key={job.id}
                          className="transition hover:bg-neutral-900/70 focus-within:bg-neutral-900/70"
                        >
                          <td className="px-4 py-4 text-sm font-semibold text-white">{job.id}</td>
                          <td className="px-4 py-4">{job.vehicle}</td>
                          <td className="px-4 py-4 text-gray-500">{job.vin}</td>
                          <td className="px-4 py-4">{job.technician}</td>
                          <td className="px-4 py-4">{job.shop}</td>
                          <td className="px-4 py-4">
                            <span
                              className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold ${getStatusStyles(
                                job.status
                              )}`}
                            >
                              {job.status}
                            </span>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </section>
        </div>
      </main>

      <footer className="border-t border-neutral-800 bg-black/40 py-4 text-center text-xs text-gray-500">
        © 2025 DriveOps-IQ — Powered by SyferStack V2 • A Syfernetics Application
      </footer>
    </div>
  );
};

type NavButtonProps = {
  label: string;
  icon: LucideIcon;
  isActive?: boolean;
  compact?: boolean;
};

function NavButton({ label, icon: Icon, isActive, compact }: NavButtonProps) {
  return (
    <button
      type="button"
      className={`flex items-center gap-2 rounded-full border border-transparent px-3 py-2 transition ${
        isActive
          ? 'bg-cherryRed/20 text-white ring-1 ring-inset ring-cherryRed/40'
          : 'text-gray-300 hover:text-white hover:ring-1 hover:ring-inset hover:ring-cherryRed/40'
      } ${compact ? 'whitespace-nowrap text-xs' : ''}`}
    >
      <Icon size={14} />
      <span>{label}</span>
    </button>
  );
}

const PlaceholderPanel: React.FC<{ title: string; description: string }> = ({
  title,
  description,
}) => (
  <div className="rounded-3xl border border-neutral-800 bg-neutral-950/60 p-10 text-center text-gray-300 shadow-inner shadow-black/40">
    <h2 className="text-2xl font-semibold text-white">{title}</h2>
    <p className="mt-4 text-sm text-gray-400">{description}</p>
  </div>
);

export const UserManagement: React.FC = () => (
  <PlaceholderPanel
    title="User Management"
    description="Manage DriveOps-IQ accounts, roles, and access policies here."
  />
);

export const SystemMetrics: React.FC = () => (
  <PlaceholderPanel
    title="System Metrics"
    description="Telemetry dashboards and service SLOs coming online soon."
  />
);

export const AIChat: React.FC = () => (
  <PlaceholderPanel
    title="AI Command Center"
    description="Conversational workflows and AI escalations will launch shortly."
  />
);

export const AIAnalytics: React.FC = () => (
  <PlaceholderPanel
    title="AI Analytics"
    description="Insights, anomaly detection, and predictive operations in progress."
  />
);

export const APIDocumentation: React.FC = () => (
  <PlaceholderPanel
    title="API Documentation"
    description="Developer portal and endpoint references are being finalized."
  />
);

export default AdminDashboard;
