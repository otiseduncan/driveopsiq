import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';

/**
 * Intro splash screen that displays the DriveOps-IQ branding briefly
 * before routing users to the login experience.
 */
export default function SplashScreen(): JSX.Element {
  const navigate = useNavigate();

  useEffect(() => {
    const timer = window.setTimeout(() => {
      navigate('/login');
    }, 3000);

    return () => window.clearTimeout(timer);
  }, [navigate]);

  return (
    <motion.div
      className="flex h-screen flex-col items-center justify-center bg-gradient-to-b from-black via-neutral-900 to-gray-900 text-white"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 1 }}
    >
      <motion.img
        src="/assets/driveops-logo.png"
        alt="DriveOps-IQ logo"
        className="mb-6 h-48 w-48"
        initial={{ scale: 0.7, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ duration: 1.2, ease: 'easeOut' }}
      />
      <h1 className="text-3xl font-bold tracking-[0.3em] text-red-500">DriveOps-IQ</h1>
      <p className="mt-4 text-sm text-gray-400">
        Powered by SyferStack V2 — A Syfernetics Application
      </p>
    </motion.div>
  );
}
