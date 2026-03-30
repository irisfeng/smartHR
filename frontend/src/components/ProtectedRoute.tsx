import { type ReactNode } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';

export default function ProtectedRoute({ children }: { children: ReactNode }) {
  const user = useAuthStore((s) => s.user);
  const token = localStorage.getItem('access_token');

  if (!token && !user) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}
