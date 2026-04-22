import React, { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Users, Wrench, MapPin, RefreshCw, Clock, BarChart3 } from "lucide-react";
import ManagerLayout from "./layouts/ManagerLayout";

export default function FieldManagerDashboard() {
  const [summary, setSummary] = useState({ active: 0, techs: 0, shops: 0, avgTime: "0 h" });
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
      const res = await fetch(`${baseUrl}/api/v1/driveops/summary`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        setSummary(await res.json());
      } else {
        setSummary({ active: 14, techs: 6, shops: 4, avgTime: "3.2 h" });
      }
    } catch {
      setSummary({ active: 14, techs: 6, shops: 4, avgTime: "3.2 h" });
    }

    setJobs([
      { id: "RO-3201", vehicle: "Tesla Model 3", shop: "AutoCal North", tech: "Alex Grant", status: "In Progress" },
      { id: "RO-3202", vehicle: "Honda CR-V", shop: "MAS West", tech: "Sara Kane", status: "Pending" },
      { id: "RO-3203", vehicle: "Ford F-150", shop: "Gerber Midtown", tech: "John Lee", status: "Completed" },
    ]);
    setLoading(false);
  };

  useEffect(() => {
    if (typeof window !== "undefined") {
      void fetchData();
    }
  }, []);

  return (
    <ManagerLayout title="DriveOps-IQ Field Manager Console">
      {/* Summary cards */}
      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-10">
        {[
          { icon: Wrench, label: "Active Jobs", value: summary.active },
          { icon: Users, label: "Technicians", value: summary.techs },
          { icon: MapPin, label: "Shops", value: summary.shops },
          { icon: Clock, label: "Avg Turnaround", value: summary.avgTime },
        ].map(({ icon: Icon, label, value }) => (
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

      {/* Job Pool */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-300">Regional Job Pool</h2>
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
                <th className="p-3">Shop</th>
                <th className="p-3">Technician</th>
                <th className="p-3">Status</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((j) => (
                <tr key={j.id} className="border-b border-gray-800 hover:bg-gray-800/40">
                  <td className="p-3 font-semibold">{j.id}</td>
                  <td className="p-3">{j.vehicle}</td>
                  <td className="p-3">{j.shop}</td>
                  <td className="p-3">{j.tech}</td>
                  <td className="p-3">
                    <StatusBadge status={j.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Analytics placeholder */}
      <section className="mt-10">
        <h2 className="text-lg font-semibold mb-3 text-gray-300">Field Analytics</h2>
        <div className="bg-gray-900/60 border border-gray-800 rounded-2xl p-6 text-gray-500 text-center">
          <BarChart3 className="w-6 h-6 inline-block text-cherryRed mr-2" />
          Technician performance, regional turnaround trends and charts will render here.
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
