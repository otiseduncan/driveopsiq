import React, { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { ClipboardCheck, DollarSign, Wrench, RefreshCw, CheckCircle } from "lucide-react";
import ManagerLayout from "./layouts/ManagerLayout";

export default function ShopManagerDashboard() {
  const [summary, setSummary] = useState({ jobs: 0, completed: 0, pending: 0, revenue: 0 });
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    try {
      const token = window.localStorage.getItem("token");
      const baseUrl = import.meta.env.VITE_API_BASE_URL;
      if (!baseUrl) {
        throw new Error("API base URL not configured");
      }
      const res = await fetch(`${baseUrl}/api/manager/shop/summary`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        setSummary(await res.json());
      } else {
        setSummary({ jobs: 10, completed: 6, pending: 4, revenue: 4800 });
      }
    } catch {
      setSummary({ jobs: 10, completed: 6, pending: 4, revenue: 4800 });
    }

    setJobs([
      { id: "RO-4101", vehicle: "Toyota Highlander", status: "Completed", tech: "Sam Rivers", invoice: true },
      { id: "RO-4102", vehicle: "Honda Accord", status: "In Progress", tech: "Amy Waters", invoice: false },
      { id: "RO-4103", vehicle: "Mazda CX-5", status: "Pending", tech: "Chris Tate", invoice: false },
    ]);
    setLoading(false);
  };

  useEffect(() => {
    if (typeof window !== "undefined") {
      void fetchData();
    }
  }, []);

  return (
    <ManagerLayout title="DriveOps-IQ Shop Manager Console">
      {/* Overview */}
      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-10">
        {[
          { label: "Total Jobs", value: summary.jobs, icon: Wrench },
          { label: "Completed", value: summary.completed, icon: CheckCircle },
          { label: "Pending", value: summary.pending, icon: ClipboardCheck },
          { label: "Revenue", value: `$${summary.revenue}`, icon: DollarSign },
        ].map(({ label, value, icon: Icon }) => (
          <motion.div
            key={label}
            whileHover={{ scale: 1.05 }}
            className="bg-gray-800/70 p-6 rounded-2xl border border-gray-700 text-center"
          >
            <Icon className="w-6 h-6 text-cherryRed mx-auto mb-2" />
            <p className="text-gray-400 text-sm">{label}</p>
            <p className="text-2xl font-bold text-white">{value}</p>
          </motion.div>
        ))}
      </section>

      {/* Shop Job Queue */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-300">Shop Job Queue</h2>
          <button
            onClick={fetchData}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 bg-cherryRed hover:bg-red-700 rounded-lg text-sm"
          >
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
            {loading ? "Refreshing..." : "Refresh"}
          </button>
        </div>
        <div className="bg-gray-900/60 border border-gray-800 rounded-2xl overflow-x-auto">
          <table className="min-w-full text-sm text-left">
            <thead className="border-b border-gray-700 text-gray-400">
              <tr>
                <th className="p-3">RO #</th>
                <th className="p-3">Vehicle</th>
                <th className="p-3">Technician</th>
                <th className="p-3">Status</th>
                <th className="p-3">Invoice</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((j) => (
                <tr key={j.id} className="border-b border-gray-800 hover:bg-gray-800/40">
                  <td className="p-3 font-semibold">{j.id}</td>
                  <td className="p-3">{j.vehicle}</td>
                  <td className="p-3">{j.tech}</td>
                  <td className="p-3">
                    <StatusBadge status={j.status} />
                  </td>
                  <td className="p-3">{j.invoice ? "✅ Ready" : "⏳ Pending"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </ManagerLayout>
  );
}

function StatusBadge({ status }) {
  const color =
    status === "Completed"
      ? "bg-green-700/40 text-green-300"
      : status === "In Progress"
      ? "bg-yellow-600/40 text-yellow-200"
      : "bg-gray-700/40 text-gray-300";
  return (
    <span className={`px-3 py-1 rounded-full text-xs font-semibold ${color}`}>
      {status}
    </span>
  );
}

