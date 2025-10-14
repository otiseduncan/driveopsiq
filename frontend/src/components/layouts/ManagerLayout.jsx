import React from "react";

export default function ManagerLayout({ title, children }) {
  return (
    <div className="min-h-screen flex flex-col bg-gradient-to-b from-black via-neutral-900 to-gray-900 text-white">
      {/* ░ Header ░ */}
      <header className="flex items-center justify-between px-6 py-3 border-b border-gray-800 bg-black/80 backdrop-blur-md sticky top-0 z-50">
        <h1 className="text-xl font-bold text-cherryRed tracking-widest">{title}</h1>
        <nav className="flex gap-5 text-sm text-gray-300">
          <NavButton label="Dashboard" />
          <NavButton label="Job Pool" />
          <NavButton label="Analytics" />
          <NavButton label="Settings" />
        </nav>
      </header>

      {/* ░ Body ░ */}
      <main className="flex-1 p-6 overflow-y-auto">{children}</main>

      {/* ░ Footer ░ */}
      <footer className="text-center text-xs py-4 border-t border-gray-800 text-gray-500">
        © 2025 DriveOps-IQ — Powered by SyferStack V2 • A Syfernetics Application
      </footer>
    </div>
  );
}

function NavButton({ label }) {
  return (
    <button className="hover:text-cherryRed transition-colors">{label}</button>
  );
}
