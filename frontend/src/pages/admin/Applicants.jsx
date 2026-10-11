import { useEffect, useState } from 'react'
import { Link, useParams, useOutletContext } from 'react-router-dom'
import { ArrowLeft, Users } from 'lucide-react'
import { apiRequest } from '../../api'
import Badge from '../../components/Badge'
import Card from '../../components/Card'
import EmptyState from '../../components/EmptyState'
import Skeleton from '../../components/Skeleton'
import { formatDate } from '../../utils/formatters'

const statuses = ['Applied', 'Shortlisted', 'Rejected', 'Selected']
export default function Applicants() {
  const { driveId } = useParams(); const { showToast } = useOutletContext(); const [applications, setApplications] = useState(null)
  function load() { apiRequest(`/drives/${driveId}/applications`).then(setApplications).catch(() => { setApplications([]); showToast('Could not load applicants.', 'error') }) }
  useEffect(load, [driveId])
  async function updateStatus(id, status) { try { await apiRequest(`/applications/${id}/status`, { method: 'PUT', body: JSON.stringify({ status }) }); setApplications(applications.map(a => a.id === id ? { ...a, status } : a)); showToast('Application status updated.') } catch (err) { showToast(err.message, 'error') } }
  if (!applications) return <Skeleton count={3} />
  return <><div className="page-heading"><div><Link className="back-link" to="/admin/drives"><ArrowLeft size={16} /> Back to drives</Link><p className="eyebrow">APPLICANT MANAGEMENT</p><h1>Applicants</h1></div></div><Card className="table-card">{applications.length === 0 ? <EmptyState title="No applicants yet" text="Applications for this drive will appear here." /> : <div className="table-wrap"><table><thead><tr><th>Student</th><th>Department</th><th>CGPA</th><th>Applied</th><th>Status</th></tr></thead><tbody>{applications.map(application => <tr key={application.id}><td><strong>{application.student.name}</strong><small>{application.student.email}<br />{application.student.register_number}</small></td><td>{application.student.department}<br /><small>{application.student.batch}</small></td><td>{application.student.cgpa}</td><td>{formatDate(application.applied_at)}</td><td><div className="status-control"><Badge status={application.status}>{application.status}</Badge><select value={application.status} onChange={e => updateStatus(application.id, e.target.value)}>{statuses.map(status => <option key={status}>{status}</option>)}</select></div></td></tr>)}</tbody></table></div>}</Card><div className="admin-helper"><Users size={18} /> Status changes are shown to students immediately.</div></>
}
