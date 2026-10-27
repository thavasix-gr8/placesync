import { useEffect, useState } from 'react'
import { BriefcaseBusiness, CheckCircle2, FileText, ListChecks } from 'lucide-react'
import { apiRequest } from '../../api'
import Card from '../../components/Card'
import EmptyState from '../../components/EmptyState'
import Skeleton from '../../components/Skeleton'
import { formatDate } from '../../utils/formatters'

export default function AdminDashboard() {
  const [data, setData] = useState(null)

  useEffect(() => {
    let active = true
    const load = () => Promise.all([apiRequest('/admin/stats'), apiRequest('/drives')])
      .then(([stats, drives]) => { if (active) setData({ stats, drives }) })
      .catch(() => { if (active) setData({ stats: { total_drives: 0, total_applications: 0, shortlisted: 0, selected: 0 }, drives: [] }) })
    load()
    const interval = window.setInterval(load, 3000)
    window.addEventListener('focus', load)
    return () => { active = false; window.clearInterval(interval); window.removeEventListener('focus', load) }
  }, [])

  if (!data) return <Skeleton count={4} />
  const cards = [
    ['Total drives', data.stats.total_drives, BriefcaseBusiness, 'cyan'],
    ['Applications', data.stats.total_applications, FileText, 'purple'],
    ['Shortlisted', data.stats.shortlisted, ListChecks, 'amber'],
    ['Selected', data.stats.selected, CheckCircle2, 'green'],
  ]

  return <><div className="page-heading"><div><p className="eyebrow">ADMIN DASHBOARD</p><h1>Placement overview</h1><p>Monitor active drives and student application progress.</p></div></div><div className="stats-grid four">{cards.map(([label, value, Icon, colour]) => <Card key={label} className={`stat-card ${colour}`}><Icon /><div><p>{label}</p><strong>{value}</strong></div></Card>)}</div><Card className="table-card"><div className="section-heading"><div><p className="eyebrow">RECENT DRIVES</p><h2>Latest placement drives</h2></div></div>{data.drives.length === 0 ? <EmptyState title="No drives created" text="Create the first placement drive from Manage drives." /> : <div className="table-wrap"><table><thead><tr><th>Company</th><th>Role</th><th>Deadline</th><th>Minimum CGPA</th><th>Applicants</th></tr></thead><tbody>{data.drives.slice(0, 5).map(drive => <tr key={drive.id}><td>{drive.company}</td><td>{drive.job_role}</td><td>{formatDate(drive.deadline)}</td><td>{drive.min_cgpa}</td><td>{drive.applicant_count}</td></tr>)}</tbody></table></div>}</Card></>
}
