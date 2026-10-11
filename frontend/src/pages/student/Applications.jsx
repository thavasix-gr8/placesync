import { useEffect, useState } from 'react'
import { Building2, CalendarDays } from 'lucide-react'
import { apiRequest } from '../../api'
import Badge from '../../components/Badge'
import Card from '../../components/Card'
import EmptyState from '../../components/EmptyState'
import Skeleton from '../../components/Skeleton'
import { formatDate } from '../../utils/formatters'

export default function Applications() {
  const [applications, setApplications] = useState(null)
  useEffect(() => { apiRequest('/applications/me').then(setApplications).catch(() => setApplications([])) }, [])
  if (!applications) return <Skeleton count={3} />
  return <><div className="page-heading"><div><p className="eyebrow">APPLICATION TRACKER</p><h1>My applications</h1></div></div>{applications.length === 0 ? <EmptyState title="No applications yet" text="Apply to an eligible drive and it will appear here." /> : <div className="application-list">{applications.map(application => <Card key={application.id} className="application-card"><div className="company-mark"><Building2 /></div><div className="application-info"><h2>{application.drive.company}</h2><p>{application.drive.job_role}</p><span><CalendarDays size={15} /> Applied {formatDate(application.applied_at)}</span></div><div className="application-status"><Badge status={application.status}>{application.status}</Badge><div className="timeline"><i className="done" /><i className={application.status !== 'Applied' ? 'done' : ''} /><i className={application.status === 'Selected' ? 'done' : ''} /></div></div></Card>)}</div>}</>
}
