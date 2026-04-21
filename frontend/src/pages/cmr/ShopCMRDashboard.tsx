import React from 'react';
import ManagerLayout from '@/components/layouts/ManagerLayout';

const ShopCMRDashboard: React.FC = () => (
  <ManagerLayout title="DriveOps-IQ Shop CMR Console">
    <div className="rounded-2xl border border-gray-800 bg-gray-900/60 p-8 text-center text-gray-300">
      Shop CMR workflows are coming online soon. Use seeded credentials to verify access.
    </div>
  </ManagerLayout>
);

export default ShopCMRDashboard;
