import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';

interface CreateRequestData {
  ro_number: string
  vin: string
  customer: string
  insurer: string
  calibration_type: string
  notes?: string
}

interface CreateRequestResponse {
  status: string
  message: string
  request: {
    id: string
    ro_number: string
    vin: string
    customer: string
    insurer: string
    calibration_type: string
    notes: string | null
    status: string
    created_at: string
  }
}

const demoFlag = import.meta.env?.VITE_DEMO_MODE;
const isDemoMode = demoFlag === undefined ? true : demoFlag === 'true';
const apiBaseUrl =
  import.meta.env?.VITE_API_BASE_URL ?? import.meta.env?.VITE_API_URL ?? '';

// API function to create a request
type ApiError = Error & { status?: number };

export default function DriveOpsRequestForm() {
  const navigate = useNavigate();
  const [formData, setFormData] = useState<CreateRequestData>({
    ro_number: '',
    vin: '',
    customer: '',
    insurer: '',
    calibration_type: '',
    notes: '',
  });

  const createRequestMutation = useMutation({
    mutationFn: async (data: CreateRequestData): Promise<CreateRequestResponse> => {
      if (isDemoMode || !apiBaseUrl) {
        await new Promise((resolve) => setTimeout(resolve, 1000));

        return {
          status: 'success',
          message: 'Request created successfully (Demo Mode)',
          request: {
            id: `demo-${Date.now()}`,
            ro_number: data.ro_number,
            vin: data.vin,
            customer: data.customer,
            insurer: data.insurer,
            calibration_type: data.calibration_type,
            notes: data.notes || null,
            status: 'pending_validation',
            created_at: new Date().toISOString(),
          },
        };
      }

      const token = typeof window !== 'undefined' ? window.localStorage.getItem('token') : null;
      const response = await fetch(`${apiBaseUrl}/api/v1/driveops/requests`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify(data),
      });

      if (response.status === 401) {
        const unauthorized: ApiError = new Error('Unauthorized');
        unauthorized.status = 401;
        throw unauthorized;
      }

      if (!response.ok) {
        const message = (await response.text()) || 'Failed to create request';
        throw new Error(message);
      }

      return (await response.json()) as CreateRequestResponse;
    },
    onSuccess: (data) => {
      console.log('Request created successfully:', data);
      alert(`Request created successfully! ID: ${data.request.id}`);
      setFormData({
        ro_number: '',
        vin: '',
        customer: '',
        insurer: '',
        calibration_type: '',
        notes: '',
      });
    },
    onError: (error) => {
      const typedError = error as ApiError;
      if (typedError.status === 401) {
        if (typeof window !== 'undefined') {
          window.localStorage.removeItem('token');
        }
        navigate('/login', { replace: true });
        return;
      }

      console.error('Failed to create request:', error);
      alert('Failed to create request. Please try again.');
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    createRequestMutation.mutate(formData);
  };

  const handleLogout = () => {
    if (typeof window !== 'undefined') {
      window.localStorage.removeItem('token');
    }
    navigate('/login', { replace: true });
  };

  const handleNavigate = (path: '/dashboard' | '/driveops') => () => {
    navigate(path, { replace: path === '/dashboard' });
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value,
    }));
  };

  return (
    <div className="relative flex min-h-screen w-full flex-col overflow-hidden bg-gradient-to-br from-black via-[#111322] to-driveops-slate">
      <div
        className="pointer-events-none absolute inset-0 bg-driveops-grid opacity-20"
        aria-hidden="true"
      />

      <header className="relative z-10 flex items-center justify-between px-6 py-6 sm:px-10">
        <div className="flex items-center space-x-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-full border border-white/20 bg-black/40">
            <img src="/assets/driveops-logo.png" alt="DriveOps IQ Logo" className="h-8 w-8" />
          </div>
          <div>
            <p className="text-xs uppercase tracking-[0.3em] text-white/60">DriveOps IQ</p>
            <p className="text-lg font-semibold text-white">Calibration Workbench</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {isDemoMode ? (
            <span className="rounded-full border border-emerald-400/40 bg-emerald-500/10 px-3 py-1 text-xs font-medium uppercase tracking-wide text-emerald-200">
              Demo Mode
            </span>
          ) : (
            <span className="rounded-full border border-sky-400/40 bg-sky-500/10 px-3 py-1 text-xs font-medium uppercase tracking-wide text-sky-200">
              Live Mode
            </span>
          )}
          <nav className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleNavigate('/dashboard')}
              className="rounded-md border border-white/15 bg-white/10 px-3 py-1 text-xs font-medium uppercase tracking-wide text-white transition hover:bg-white/20"
            >
              Dashboard
            </button>
            <button
              type="button"
              onClick={handleNavigate('/driveops')}
              className="rounded-md border border-white/15 bg-white/10 px-3 py-1 text-xs font-medium uppercase tracking-wide text-white transition hover:bg-white/20"
            >
              New Request
            </button>
            <button
              type="button"
              onClick={handleLogout}
              className="rounded-md border border-driveops-red/40 bg-driveops-red/20 px-3 py-1 text-xs font-medium uppercase tracking-wide text-driveops-red hover:bg-driveops-red/30"
            >
              Log Out
            </button>
          </nav>
        </div>
      </header>

      <div className="relative z-10 flex flex-1 flex-col items-center justify-center px-4 pb-16 pt-6 sm:px-8">
        <div className="w-full max-w-5xl rounded-3xl border border-white/10 bg-black/60 p-8 shadow-2xl backdrop-blur-xl sm:p-12">
          <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <h1 className="text-3xl font-semibold tracking-tight text-white sm:text-4xl">
                Create Calibration Request
              </h1>
              <p className="mt-2 max-w-xl text-sm text-gray-300">
                Submit a new DriveOps IQ workflow for ADAS, camera, radar, lidar, or full system
                calibration. All fields are required unless marked optional.
              </p>
            </div>
            {isDemoMode ? (
              <div className="rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-gray-200 shadow-lg ring-1 ring-white/10">
                <p className="font-medium text-white">Demo Mode Active</p>
                <p className="text-xs text-gray-300">
                  Requests are simulated client-side while the API is offline.
                </p>
              </div>
            ) : (
              <div className="rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-gray-200 shadow-lg ring-1 ring-white/10">
                <p className="font-medium text-white">Connected to SyferStack</p>
                <p className="text-xs text-gray-300">
                  Requests will be submitted to the live backend using your authenticated session.
                </p>
              </div>
            )}
          </div>

          <form
            onSubmit={handleSubmit}
            className="grid gap-6 rounded-2xl border border-white/5 bg-white/5 p-6 shadow-inner ring-1 ring-white/10 sm:p-8"
          >
            <div className="grid gap-6 sm:grid-cols-2">
              <div>
                <label
                  htmlFor="ro_number"
                  className="mb-2 block text-xs font-semibold uppercase tracking-wide text-gray-300"
                >
                  RO Number *
                </label>
                <input
                  type="text"
                  id="ro_number"
                  name="ro_number"
                  value={formData.ro_number}
                  onChange={handleInputChange}
                  required
                  className="w-full rounded-lg border border-white/10 bg-black/40 px-4 py-3 text-sm text-white placeholder-gray-500 outline-none transition focus:border-driveops-red focus:ring-2 focus:ring-driveops-red/60"
                  placeholder="e.g. RO-24517"
                />
              </div>

              <div>
                <label
                  htmlFor="vin"
                  className="mb-2 block text-xs font-semibold uppercase tracking-wide text-gray-300"
                >
                  VIN *
                </label>
                <input
                  type="text"
                  id="vin"
                  name="vin"
                  value={formData.vin}
                  onChange={handleInputChange}
                  required
                  maxLength={17}
                  className="w-full rounded-lg border border-white/10 bg-black/40 px-4 py-3 text-sm text-white placeholder-gray-500 outline-none transition focus:border-driveops-red focus:ring-2 focus:ring-driveops-red/60"
                  placeholder="17-character VIN"
                />
              </div>
            </div>

            <div className="grid gap-6 sm:grid-cols-2">
              <div>
                <label
                  htmlFor="customer"
                  className="mb-2 block text-xs font-semibold uppercase tracking-wide text-gray-300"
                >
                  Customer *
                </label>
                <input
                  type="text"
                  id="customer"
                  name="customer"
                  value={formData.customer}
                  onChange={handleInputChange}
                  required
                  className="w-full rounded-lg border border-white/10 bg-black/40 px-4 py-3 text-sm text-white placeholder-gray-500 outline-none transition focus:border-driveops-red focus:ring-2 focus:ring-driveops-red/60"
                  placeholder="Customer name"
                />
              </div>

              <div>
                <label
                  htmlFor="insurer"
                  className="mb-2 block text-xs font-semibold uppercase tracking-wide text-gray-300"
                >
                  Insurer *
                </label>
                <input
                  type="text"
                  id="insurer"
                  name="insurer"
                  value={formData.insurer}
                  onChange={handleInputChange}
                  required
                  className="w-full rounded-lg border border-white/10 bg-black/40 px-4 py-3 text-sm text-white placeholder-gray-500 outline-none transition focus:border-driveops-red focus:ring-2 focus:ring-driveops-red/60"
                  placeholder="Insurance provider"
                />
              </div>
            </div>

            <div className="grid gap-6 sm:grid-cols-2">
              <div>
                <label
                  htmlFor="calibration_type"
                  className="mb-2 block text-xs font-semibold uppercase tracking-wide text-gray-300"
                >
                  Calibration Type *
                </label>
                <select
                  id="calibration_type"
                  name="calibration_type"
                  value={formData.calibration_type}
                  onChange={handleInputChange}
                  required
                  className="w-full rounded-lg border border-white/10 bg-black/40 px-4 py-3 text-sm text-white outline-none transition focus:border-driveops-red focus:ring-2 focus:ring-driveops-red/60"
                >
                  <option value="" className="text-gray-700">
                    Select calibration type
                  </option>
                  <option value="ADAS Calibration">ADAS Calibration</option>
                  <option value="Camera Calibration">Camera Calibration</option>
                  <option value="Radar Calibration">Radar Calibration</option>
                  <option value="Lidar Calibration">Lidar Calibration</option>
                  <option value="Full System Calibration">Full System Calibration</option>
                </select>
              </div>

              <div>
                <label
                  htmlFor="notes"
                  className="mb-2 block text-xs font-semibold uppercase tracking-wide text-gray-300"
                >
                  Notes (Optional)
                </label>
                <textarea
                  id="notes"
                  name="notes"
                  value={formData.notes}
                  onChange={handleInputChange}
                  rows={3}
                  className="w-full rounded-lg border border-white/10 bg-black/40 px-4 py-3 text-sm text-white placeholder-gray-500 outline-none transition focus:border-driveops-red focus:ring-2 focus:ring-driveops-red/60"
                  placeholder="Provide any additional context for this request"
                />
              </div>
            </div>

            <div className="flex flex-col items-stretch gap-3 sm:flex-row sm:justify-end">
              <button
                type="button"
                onClick={() =>
                  setFormData({
                    ro_number: '',
                    vin: '',
                    customer: '',
                    insurer: '',
                    calibration_type: '',
                    notes: '',
                  })
                }
                className="inline-flex items-center justify-center rounded-lg border border-white/10 bg-white/5 px-5 py-2.5 text-sm font-semibold text-gray-200 transition hover:border-white/30 hover:bg-white/10 focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-black focus-visible:ring-white/40"
              >
                Reset Form
              </button>
              <button
                type="submit"
                disabled={createRequestMutation.isPending}
                className="inline-flex items-center justify-center rounded-lg bg-driveops-red px-6 py-2.5 text-sm font-semibold uppercase tracking-wide text-white shadow-lg shadow-driveops-red/30 transition hover:bg-red-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-black focus-visible:ring-driveops-red disabled:cursor-not-allowed disabled:opacity-60"
              >
                {createRequestMutation.isPending ? 'Creating...' : 'Create Request'}
              </button>
            </div>
          </form>

          {createRequestMutation.isError ? (
            <div className="mt-6 rounded-xl border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-200">
              Error: {createRequestMutation.error?.message}
            </div>
          ) : null}

          {createRequestMutation.isSuccess ? (
            <div className="mt-6 rounded-xl border border-emerald-500/40 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-100">
              Request created successfully!
            </div>
          ) : null}
        </div>
      </div>
    </div>
  )
}
