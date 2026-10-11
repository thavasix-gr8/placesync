import { useEffect, useState } from 'react'
import { BriefcaseBusiness, CheckCircle2, FileText } from 'lucide-react'
import { apiRequest } from '../../api'
import Card from '../../components/Card'
import Skeleton from '../../components/Skeleton'

export default function StudentDashboard() {
  const [stats, setStats] = useState(null)
  useEffect(() => { Promise.all([apiRequest('/drives'), apiRequest('/applications/me')]).then(([drives, applications]) => setStats({ eligible: drives.filter(d => d.eligible).length, applied: applications.length, shortlisted: applications.filter(a => a.status === 'Shortlisted').length })).catch(() => setStats({ eligible: 0, applied: 0, shortlisted: 0 })) }, [])
  if (!stats) return <Skeleton count={3} />
  const cards = [['Eligible drives', stats.eligible, BriefcaseBusiness, 'cyan'], ['Applied', stats.applied, FileText, 'purple'], ['Shortlisted', stats.shortlisted, CheckCircle2, 'amber']]
  return <><div className="page-heading"><div><p className="eyebrow">STUDENT DASHBOARD</p><h1>Your placement space</h1></div></div><div className="stats-grid">{cards.map(([label, value, Icon, colour]) => <Card key={label} className={`stat-card ${colour}`}><Icon /><div><p>{label}</p><strong>{value}</strong></div></Card>)}</div><Card className="highlight-card"><p className="eyebrow">YOUR NEXT STEP</p><h2>Check eligible drives</h2><p>The drive list checks every rule against your current profile and shows a clear reason whenever you do not qualify.</p></Card></>
}
