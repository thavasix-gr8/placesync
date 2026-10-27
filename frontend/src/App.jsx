import { Navigate, Route, Routes } from 'react-router-dom'
import AppLayout from './components/AppLayout'
import ProtectedRoute from './components/ProtectedRoute'
import Login from './pages/Login'
import Signup from './pages/Signup'
import StudentDashboard from './pages/student/Dashboard'
import StudentDrives from './pages/student/Drives'
import StudentApplications from './pages/student/Applications'
import StudentProfile from './pages/student/Profile'
import AdminDashboard from './pages/admin/Dashboard'
import AdminApplicants from './pages/admin/DriveApplicants'
import AdminDrives from './pages/admin/Drives'
import Applicants from './pages/admin/Applicants'

export default function App() {
  return <Routes>
    <Route path="/login" element={<Login />} />
    <Route path="/signup" element={<Signup />} />
    <Route element={<ProtectedRoute role="student" />}><Route element={<AppLayout />}>
      <Route path="/student/dashboard" element={<StudentDashboard />} />
      <Route path="/student/drives" element={<StudentDrives />} />
      <Route path="/student/applications" element={<StudentApplications />} />
      <Route path="/student/profile" element={<StudentProfile />} />
    </Route></Route>
    <Route element={<ProtectedRoute role="admin" />}><Route element={<AppLayout />}>
      <Route path="/admin/dashboard" element={<AdminDashboard />} />
      <Route path="/admin/applicants" element={<AdminApplicants />} />
      <Route path="/admin/drives" element={<AdminDrives />} />
      <Route path="/admin/drives/:driveId/applicants" element={<Applicants />} />
    </Route></Route>
    <Route path="*" element={<Navigate to="/login" replace />} />
  </Routes>
}
