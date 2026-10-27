import { useEffect, useState } from 'react'
import { Link, useOutletContext, useParams } from 'react-router-dom'
import { Archive, ArrowLeft, Download, Eye, FileSpreadsheet, Users, X } from 'lucide-react'
import { API_URL, apiRequest } from '../../api'
import Badge from '../../components/Badge'
import Button from '../../components/Button'
import Card from '../../components/Card'
import EmptyState from '../../components/EmptyState'
import Skeleton from '../../components/Skeleton'
import { formatDate } from '../../utils/formatters'

const statuses = ['Applied', 'Shortlisted', 'Rejected', 'Selected']

export default function Applicants() {
  const { driveId } = useParams()
  const { showToast } = useOutletContext()
  const [applications, setApplications] = useState(null)
  const [loadingResumeId, setLoadingResumeId] = useState(null)
  const [resumeViewer, setResumeViewer] = useState(null)
  const [statusFilter, setStatusFilter] = useState('All')
  const [selectedIds, setSelectedIds] = useState(() => new Set())
  const [bulkStatus, setBulkStatus] = useState('')
  const [exporting, setExporting] = useState(null)

  useEffect(() => {
    let active = true
    const load = (showError = false) => apiRequest(`/drives/${driveId}/applications`)
      .then(data => { if (active) setApplications(data) })
      .catch(() => {
        if (active && showError) {
          setApplications([])
          showToast('Could not load applicants.', 'error')
        }
      })
    load(true)
    const interval = window.setInterval(() => load(), 3000)
    return () => { active = false; window.clearInterval(interval) }
  }, [driveId, showToast])

  useEffect(() => {
    if (!resumeViewer) return undefined
    return () => URL.revokeObjectURL(resumeViewer.url)
  }, [resumeViewer])

  async function updateStatus(id, status) {
    try {
      await apiRequest(`/applications/${id}/status`, { method: 'PUT', body: JSON.stringify({ status }) })
      setApplications(current => current.map(application => application.id === id ? { ...application, status } : application))
      showToast('Application status updated.')
    } catch (error) {
      showToast(error.message, 'error')
    }
  }

  async function requestResume(application, action) {
    setLoadingResumeId(application.id)
    try {
      const endpoint = `/admin/drives/${driveId}/applications/${application.id}/resume${action === 'view' ? '/view' : ''}`
      const response = await fetch(`${API_URL}${endpoint}`, {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
      })
      if (!response.ok) {
        const body = await response.json().catch(() => null)
        throw new Error(body?.detail || 'Resume request failed.')
      }
      const blob = await response.blob()
      const header = response.headers.get('Content-Disposition') || ''
      const suggestedName = header.match(/filename="?([^";]+)"?/i)?.[1] || 'resume.pdf'
      const filename = suggestedName.split(/[\\/]/).pop()
      const url = URL.createObjectURL(blob)
      if (action === 'view') {
        setResumeViewer({ url, filename })
      } else {
        const link = document.createElement('a')
        link.href = url
        link.download = filename
        link.click()
        window.setTimeout(() => URL.revokeObjectURL(url), 1000)
      }
    } catch (error) {
      showToast(error.message, 'error')
    } finally {
      setLoadingResumeId(null)
    }
  }

  const visibleApplications = applications?.filter(application =>
    statusFilter === 'All' || application.status === statusFilter
  ) || []

  function toggleApplication(id) {
    setSelectedIds(current => {
      const next = new Set(current)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  function toggleVisibleApplications(checked) {
    setSelectedIds(current => {
      const next = new Set(current)
      visibleApplications.forEach(application => {
        if (checked) next.add(application.id)
        else next.delete(application.id)
      })
      return next
    })
  }

  async function changeSelectedStatus() {
    if (!bulkStatus || selectedIds.size === 0) return
    try {
      const result = await apiRequest(`/drives/${driveId}/applications/status`, {
        method: 'PUT',
        body: JSON.stringify({ application_ids: [...selectedIds], status: bulkStatus }),
      })
      const changedIds = new Set(selectedIds)
      setApplications(current => current.map(application => changedIds.has(application.id)
        ? { ...application, status: result.status }
        : application))
      setSelectedIds(new Set())
      setBulkStatus('')
      showToast(`Updated ${result.updated} application${result.updated === 1 ? '' : 's'}.`)
    } catch (error) {
      showToast(error.message, 'error')
    }
  }

  async function exportFile(kind) {
    setExporting(kind)
    try {
      const path = kind === 'csv'
        ? `/admin/drives/${driveId}/applicants.csv`
        : `/admin/drives/${driveId}/resumes.zip`
      const response = await fetch(`${API_URL}${path}`, {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
      })
      if (!response.ok) {
        const body = await response.json().catch(() => null)
        throw new Error(body?.detail || 'Export could not be downloaded.')
      }
      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = kind === 'csv' ? `drive_${driveId}_applicants.csv` : `drive_${driveId}_resumes.zip`
      link.click()
      window.setTimeout(() => URL.revokeObjectURL(url), 1000)
      if (kind === 'csv') {
        showToast('Applicant CSV downloaded.')
      } else {
        const skipped = Number(response.headers.get('X-Resumes-Skipped') || 0)
        showToast(`Resume ZIP downloaded. ${skipped} applicant${skipped === 1 ? '' : 's'} skipped because they have no resume.`)
      }
    } catch (error) {
      showToast(error.message, 'error')
    } finally {
      setExporting(null)
    }
  }

  if (!applications) return <Skeleton count={3} />

  return <>
    <div className="page-heading">
      <div>
        <Link className="back-link" to="/admin/drives"><ArrowLeft size={16} /> Back to drives</Link>
        <p className="eyebrow">APPLICANT MANAGEMENT</p>
        <h1>Applicants</h1>
      </div>
    </div>
    <div className="applicant-export-actions">
      <Button type="button" variant="ghost" disabled={exporting !== null} onClick={() => exportFile('csv')}>
        <FileSpreadsheet size={16} /> {exporting === 'csv' ? 'Exporting CSV…' : 'Export CSV'}
      </Button>
      <Button type="button" variant="ghost" disabled={exporting !== null} onClick={() => exportFile('zip')}>
        <Archive size={16} /> {exporting === 'zip' ? 'Preparing ZIP…' : 'Download all resumes'}
      </Button>
    </div>
    <div className="applicant-table-tools">
      <label>Status filter
        <select value={statusFilter} onChange={event => setStatusFilter(event.target.value)}>
          {['All', 'Applied', 'Shortlisted', 'Selected', 'Rejected'].map(status => <option key={status}>{status}</option>)}
        </select>
      </label>
      <div className="bulk-status-controls">
        <span>{selectedIds.size} selected</span>
        <select value={bulkStatus} onChange={event => setBulkStatus(event.target.value)} aria-label="Change selected applicants to status">
          <option value="">Change status</option>
          {['Shortlisted', 'Selected', 'Rejected'].map(status => <option key={status}>{status}</option>)}
        </select>
        <Button type="button" variant="ghost" disabled={!bulkStatus || selectedIds.size === 0} onClick={changeSelectedStatus}>Apply</Button>
      </div>
    </div>
    <Card className="table-card">
      {applications.length === 0 ? <EmptyState title="No applicants yet" text="Applications for this drive will appear here." /> : visibleApplications.length === 0 ?
        <EmptyState title="No applications with this status" text="Choose another status filter to see applicants." /> :
        <div className="table-wrap">
          <table className="applicants-table">
            <thead><tr>
              <th><input type="checkbox" aria-label="Select all visible applicants" checked={visibleApplications.length > 0 && visibleApplications.every(application => selectedIds.has(application.id))} onChange={event => toggleVisibleApplications(event.target.checked)} /></th>
              <th>Student</th><th>Register number</th><th>Department</th><th>CGPA</th><th>Arrears</th><th>Applied</th><th>Status</th><th>Resume</th>
            </tr></thead>
            <tbody>{visibleApplications.map(application => <tr key={application.id}>
              <td><input type="checkbox" aria-label={`Select ${application.student.name}`} checked={selectedIds.has(application.id)} onChange={() => toggleApplication(application.id)} /></td>
              <td><strong>{application.student.name}</strong><small>{application.student.email}</small></td>
              <td>{application.student.register_number}</td>
              <td>{application.student.department}<br /><small>{application.student.batch}</small></td>
              <td>{application.student.cgpa}</td>
              <td>{application.student.arrears}</td>
              <td>{formatDate(application.applied_at)}</td>
              <td><div className="status-control">
                <Badge status={application.status}>{application.status}</Badge>
                <select value={application.status} onChange={event => updateStatus(application.id, event.target.value)}>
                  {statuses.map(status => <option key={status}>{status}</option>)}
                </select>
              </div></td>
              <td>{application.resume_id ? <div className="resume-action-buttons">
                <Button variant="ghost" disabled={loadingResumeId === application.id} onClick={() => requestResume(application, 'view')}>
                  <Eye size={15} /> View resume
                </Button>
                <Button variant="ghost" disabled={loadingResumeId === application.id} onClick={() => requestResume(application, 'download')}>
                  <Download size={15} /> Download
                </Button>
              </div> : <span className="muted">No resume</span>}</td>
            </tr>)}</tbody>
          </table>
        </div>}
    </Card>
    <div className="admin-helper"><Users size={18} /> Status changes are shown to students immediately.</div>
    {resumeViewer && <div className="resume-preview-overlay" role="presentation" onClick={() => setResumeViewer(null)}>
      <section className="resume-preview-modal" role="dialog" aria-modal="true" aria-label={`${resumeViewer.filename} preview`} onClick={event => event.stopPropagation()}>
        <div className="resume-preview-header">
          <strong>{resumeViewer.filename}</strong>
          <button className="icon-button" type="button" aria-label="Close resume preview" onClick={() => setResumeViewer(null)}><X size={18} /></button>
        </div>
        <iframe title="Applicant resume preview" src={resumeViewer.url} />
      </section>
    </div>}
  </>
}
