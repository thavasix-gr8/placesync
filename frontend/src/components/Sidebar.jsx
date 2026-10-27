import { BarChart3, BriefcaseBusiness, FileText, LayoutDashboard, PlusCircle, UserRound, Users } from 'lucide-react'
import { NavLink } from 'react-router-dom'

const studentLinks = [
  ['Dashboard', '/student/dashboard', LayoutDashboard], ['Eligible drives', '/student/drives', BriefcaseBusiness],
  ['My applications', '/student/applications', FileText], ['My profile', '/student/profile', UserRound],
]
const adminLinks = [
  ['Dashboard', '/admin/dashboard', BarChart3], ['Applicants', '/admin/applicants', Users],
  ['Manage drives', '/admin/drives', PlusCircle],
]

export default function Sidebar({ role, open, close }) {
  const links = role === 'admin' ? adminLinks : studentLinks
  return <aside className={`sidebar ${open ? 'open' : ''}`}>
    <div className="sidebar-title">{role === 'admin' ? 'Admin panel' : 'Student panel'}</div>
    <nav>{links.map(([label, path, Icon]) => <NavLink key={path} to={path} onClick={close}><Icon size={18} />{label}</NavLink>)}</nav>
  </aside>
}
