import { useEffect, useState } from 'react'
import { Building2, CalendarDays, CircleAlert, GraduationCap, Landmark, Send } from 'lucide-react'
import { apiRequest } from '../../api'
import Badge from '../../components/Badge'
import Button from '../../components/Button'
import Card from '../../components/Card'
import EmptyState from '../../components/EmptyState'
import Skeleton from '../../components/Skeleton'
import { formatDate } from '../../utils/formatters'
import { useOutletContext } from 'react-router-dom'

export default function StudentDrives() {
  const { showToast } = useOutletContext(); const [drives, setDrives] = useState(null); const [applying, setApplying] = useState(null)
  function load() { apiRequest('/drives').then(setDrives).catch(() => { setDrives([]); showToast('Could not load drives.', 'error') }) }
  useEffect(load, [])
  async function apply(drive) { setApplying(drive.id); try { await apiRequest(`/drives/${drive.id}/apply`, { method: 'POST' }); showToast(`Application sent to ${drive.company}`); load() } catch (err) { showToast(err.message, 'error') } finally { setApplying(null) } }
  if (!drives) return <Skeleton count={4} />
  return <><div className="page-heading"><div><p className="eyebrow">ELIGIBILITY ENGINE</p><h1>Placement drives</h1><p>Every drive is checked against your saved profile.</p></div></div>{drives.length === 0 ? <EmptyState title="No drives yet" text="Your placement team has not posted any drives." /> : <div className="drive-grid">{drives.map(drive => <Card key={drive.id} className={`drive-card ${!drive.eligible ? 'not-eligible' : ''}`}><div className="card-top"><div className="company-mark"><Building2 /></div><Badge status={drive.eligible ? 'Eligible' : 'Not eligible'}>{drive.eligible ? 'Eligible' : 'Not eligible'}</Badge></div><h2>{drive.company}</h2><p className="role">{drive.job_role}</p><p className="muted drive-description">{drive.description}</p><div className="drive-meta"><span><CalendarDays />Deadline: {formatDate(drive.deadline)}</span></div><div className="rule-chips"><span><GraduationCap />CGPA {drive.min_cgpa}+</span><span><CircleAlert />Max {drive.max_arrears} arrears</span><span><Landmark />{drive.allowed_departments || 'All departments'}</span></div>{drive.eligible ? <Button onClick={() => apply(drive)} disabled={applying === drive.id}>{applying === drive.id ? 'Applying...' : <><Send size={16} /> Apply now</>}</Button> : <div className="reason-box"><strong>Why you are not eligible</strong>{drive.reasons.map(reason => <p key={reason}>{reason}</p>)}</div>}</Card>)}</div>}</>
}
