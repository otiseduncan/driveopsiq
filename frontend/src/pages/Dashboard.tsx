import { Navigate } from 'react-router-dom';
import DriveOpsRequestForm from '@/modules/driveops_iq/DriveOpsRequestForm';

const Dashboard: React.FC = () => {
  if (typeof window !== 'undefined') {
    const token = window.localStorage.getItem('token');
    if (!token) {
      return <Navigate to="/login" replace />;
    }
  }

  return <DriveOpsRequestForm />;
};

export default Dashboard;
