import { LogOut, Menu, X } from 'lucide-react'

export default function Navbar({ user, onLogout, sidebarOpen, setSidebarOpen }) {
  return <header className="navbar">
    <button className="icon-button mobile-menu" onClick={() => setSidebarOpen(!sidebarOpen)}>{sidebarOpen ? <X /> : <Menu />}</button>
    <div><strong>Place<span>Sync</span></strong><small>Placement dashboard</small></div>
    <div className="user-menu"><span>{user?.name}</span><button className="icon-button" title="Log out" onClick={onLogout}><LogOut size={18} /></button></div>
  </header>
}
