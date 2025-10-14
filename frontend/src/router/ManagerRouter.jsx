import React from "react";
import FieldManagerDashboard from "../components/FieldManagerDashboard";
import ShopManagerDashboard from "../components/ShopManagerDashboard";

export default function ManagerRouter() {
  const role =
    typeof window !== "undefined" ? window.localStorage.getItem("role") : null;
  if (role === "manager_field") return <FieldManagerDashboard />;
  if (role === "manager_shop") return <ShopManagerDashboard />;
  return <div className="text-white p-6">Unauthorized Access</div>;
}
