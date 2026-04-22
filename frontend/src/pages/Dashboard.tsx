import { Navigate } from 'react-router-dom';

const ROLE_ROUTES: Record<string, string> = {
  super_admin: '/dashboard/admin',
  admin: '/dashboard/admin',
  manager_field: '/dashboard/manager/field',
  manager_shop: '/dashboard/manager/shop',
  cmr_shop: '/dashboard/cmr/shop',
  cmr_mobile: '/dashboard/cmr/mobile',
  technician: '/dashboard/technician',
};

const Dashboard: React.FC = () => {
  const token = typeof window !== 'undefined' ? window.localStorage.getItem('token') : null;
  if (!token) {
    return <Navigate to="/login" replace />;
  }

  const role = typeof window !== 'undefined' ? window.localStorage.getItem('role') : null;
  const destination = (role && ROLE_ROUTES[role]) ?? '/unauthorized';
  return <Navigate to={destination} replace />;
};

export default Dashboard;

