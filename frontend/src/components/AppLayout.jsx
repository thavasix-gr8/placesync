import { useEffect, useState } from 'react'
import { Outlet, useNavigate } from 'react-router-dom'
import { apiRequest } from '../api'
import Navbar from './Navbar'
import Sidebar from './Sidebar'
import Toast from './Toast'

export default function AppLayout() {
  const navigate = useNavigate()
  const [user, setUser] = useState(null)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [toast, setToast] = useState(null)

  function showToast(message, type = 'success') {
    setToast({ message, type })
    window.setTimeout(() => setToast(null), 3500)
  }

  async function refreshUser() {
    try { setUser(await apiRequest('/me')) } catch {
      localStorage.clear()
      navigate('/login')
    }
  }

  useEffect(() => { refreshUser() }, [])

  function logout() {
    localStorage.clear()
    navigate('/login')
  }

  return <div className="app-shell">
    <Navbar user={user} onLogout={logout} sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
    <Sidebar role={localStorage.getItem('role')} open={sidebarOpen} close={() => setSidebarOpen(false)} />
    <main className="page-content"><Outlet context={{ user, refreshUser, showToast }} /></main>
    <Toast toast={toast} onClose={() => setToast(null)} />
  </div>
}
