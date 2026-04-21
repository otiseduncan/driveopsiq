import React from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import FieldManagerDashboard from "../components/FieldManagerDashboard";
import ShopManagerDashboard from "../components/ShopManagerDashboard";

export default function ManagerRouter() {
  const role =
    typeof window !== "undefined" ? window.localStorage.getItem("role") : null;

  // Redirect to correct manager dashboard based on role
  if (role === "manager_field") {
    return (
      <Routes>
        <Route path="/field" element={<FieldManagerDashboard />} />
        <Route path="*" element={<Navigate to="/dashboard/manager/field" replace />} />
      </Routes>
    );
  }

  if (role === "manager_shop") {
    return (
      <Routes>
        <Route path="/shop" element={<ShopManagerDashboard />} />
        <Route path="*" element={<Navigate to="/dashboard/manager/shop" replace />} />
      </Routes>
    );
  }

  // If role doesn't match any manager type, redirect to unauthorized
  return <Navigate to="/unauthorized" replace />;
}
