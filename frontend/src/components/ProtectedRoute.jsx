import { Navigate, Outlet } from 'react-router-dom'

export default function ProtectedRoute({ role }) {
  const token = localStorage.getItem('token')
  const savedRole = localStorage.getItem('role')
  if (!token) return <Navigate to="/login" replace />
  if (role && savedRole !== role) return <Navigate to={savedRole === 'admin' ? '/admin/dashboard' : '/student/dashboard'} replace />
  return <Outlet />
}
