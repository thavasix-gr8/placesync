import { useCallback, useEffect, useState } from 'react'
import { BriefcaseBusiness, CheckCircle2, FileText, ListChecks, Trash2 } from 'lucide-react'
import { useOutletContext } from 'react-router-dom'
import { apiRequest } from '../../api'
import Button from '../../components/Button'
import Card from '../../components/Card'
import AnnouncementModal from '../../components/AnnouncementModal'
import EmptyState from '../../components/EmptyState'
import Skeleton from '../../components/Skeleton'
import { formatDate } from '../../utils/formatters'

function AnnouncementRow({ item, onOpen, onDelete }) {
  return <article className="announcement-list-row">
    <button className="announcement-row-content" type="button" onClick={() => onOpen(item)}>
      <span className="announcement-row-heading">
        <strong>{item.title}</strong>
        <span className="announcement-row-meta">
          {item.drive_company && <span>Drive: {item.drive_company}</span>}
          <time>{formatDate(item.created_at)}</time>
        </span>
      </span>
      <span className="announcement-row-message">{item.message}</span>
    </button>
    {onDelete && <button className="icon-button danger" type="button" title="Delete announcement" aria-label="Delete this announcement" onClick={() => onDelete(item.id)}><Trash2 size={16} /></button>}
  </article>
}

function AnnouncementDetails({ item }) {
  return <div className="announcement-detail">
    <p className="announcement-detail-message">{item.message}</p>
    <div className="announcement-row-meta">
      {item.drive_company && <span>Drive: {item.drive_company}</span>}
      <time>{formatDate(item.created_at)}</time>
    </div>
  </div>
}

export default function AdminDashboard() {
  const { showToast } = useOutletContext()
  const [data, setData] = useState(null)
  const [announcements, setAnnouncements] = useState([])
  const [announcementTitle, setAnnouncementTitle] = useState('')
  const [announcementMessage, setAnnouncementMessage] = useState('')
  const [announcementDrive, setAnnouncementDrive] = useState('')
  const [savingAnnouncement, setSavingAnnouncement] = useState(false)
  const [showAllAnnouncements, setShowAllAnnouncements] = useState(false)
  const [selectedAnnouncement, setSelectedAnnouncement] = useState(null)
  const closeAllAnnouncements = useCallback(() => setShowAllAnnouncements(false), [])
  const closeAnnouncementDetails = useCallback(() => setSelectedAnnouncement(null), [])

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

  useEffect(() => {
    apiRequest('/admin/announcements').then(setAnnouncements).catch(() => setAnnouncements([]))
  }, [])

  async function createAnnouncement(event) {
    event.preventDefault()
    setSavingAnnouncement(true)
    try {
      const announcement = await apiRequest('/admin/announcements', {
        method: 'POST',
        body: JSON.stringify({
          title: announcementTitle,
          message: announcementMessage,
          drive_id: announcementDrive ? Number(announcementDrive) : null,
        }),
      })
      setAnnouncements(current => [announcement, ...current])
      setAnnouncementTitle('')
      setAnnouncementMessage('')
      setAnnouncementDrive('')
      showToast('Announcement posted.')
    } catch (error) {
      showToast(error.message, 'error')
    } finally {
      setSavingAnnouncement(false)
    }
  }

  async function removeAnnouncement(id) {
    if (!window.confirm('Delete this announcement?')) return
    try {
      await apiRequest(`/admin/announcements/${id}`, { method: 'DELETE' })
      setAnnouncements(current => current.filter(item => item.id !== id))
      setSelectedAnnouncement(current => current?.id === id ? null : current)
      showToast('Announcement deleted.')
    } catch (error) {
      showToast(error.message, 'error')
    }
  }

  if (!data) return <Skeleton count={4} />
  const cards = [
    ['Total drives', data.stats.total_drives, BriefcaseBusiness, 'cyan'],
    ['Applications', data.stats.total_applications, FileText, 'purple'],
    ['Shortlisted', data.stats.shortlisted, ListChecks, 'amber'],
    ['Selected', data.stats.selected, CheckCircle2, 'green'],
  ]

  function openAnnouncement(item) {
    setShowAllAnnouncements(false)
    setSelectedAnnouncement(item)
  }

  function renderAnnouncementList(items) {
    return items.length === 0 ? <p className="muted">You have not posted any announcements yet.</p> :
      <div className="announcement-compact-list">{items.map(item => <AnnouncementRow key={item.id} item={item} onOpen={openAnnouncement} onDelete={removeAnnouncement} />)}</div>
  }

  return <>
    <div className="page-heading"><div><p className="eyebrow">ADMIN DASHBOARD</p><h1>Placement overview</h1><p>Monitor active drives and student application progress.</p></div></div>
    <div className="stats-grid four">{cards.map(([label, value, Icon, colour]) => <Card key={label} className={`stat-card ${colour}`}><Icon /><div><p>{label}</p><strong>{value}</strong></div></Card>)}</div>
    <Card className="admin-announcements-card">
      <div className="section-heading"><div><p className="eyebrow">STUDENT UPDATES</p><h2>Post an announcement</h2></div></div>
      <form className="admin-announcement-form" onSubmit={createAnnouncement}>
        <label>Title<input maxLength="120" value={announcementTitle} onChange={event => setAnnouncementTitle(event.target.value)} required /></label>
        <label>Message<textarea maxLength="2000" value={announcementMessage} onChange={event => setAnnouncementMessage(event.target.value)} required /></label>
        <label>Related drive (optional)
          <select value={announcementDrive} onChange={event => setAnnouncementDrive(event.target.value)}>
            <option value="">No linked drive</option>
            {data.drives.map(drive => <option value={drive.id} key={drive.id}>{drive.company} — {drive.job_role}</option>)}
          </select>
        </label>
        <Button className="admin-announcement-submit" disabled={savingAnnouncement}>{savingAnnouncement ? 'Posting…' : 'Post announcement'}</Button>
      </form>
      <div className="admin-announcement-list">
        <div className="announcement-list-heading"><h3>Announcements</h3>{announcements.length > 0 && <Button type="button" variant="ghost" onClick={() => setShowAllAnnouncements(true)}>View all</Button>}</div>
        {renderAnnouncementList(announcements.slice(0, 5))}
      </div>
    </Card>
    <Card className="table-card"><div className="section-heading"><div><p className="eyebrow">RECENT DRIVES</p><h2>Latest placement drives</h2></div></div>{data.drives.length === 0 ? <EmptyState title="No drives created" text="Create the first placement drive from Manage drives." /> : <div className="table-wrap"><table><thead><tr><th>Company</th><th>Role</th><th>Deadline</th><th>Minimum CGPA</th><th>Applicants</th></tr></thead><tbody>{data.drives.slice(0, 5).map(drive => <tr key={drive.id}><td>{drive.company}</td><td>{drive.job_role}</td><td>{formatDate(drive.deadline)}</td><td>{drive.min_cgpa}</td><td>{drive.applicant_count}</td></tr>)}</tbody></table></div>}</Card>
    {showAllAnnouncements && <AnnouncementModal title="All announcements" onClose={closeAllAnnouncements} className="announcement-list-modal">{renderAnnouncementList(announcements)}</AnnouncementModal>}
    {selectedAnnouncement && <AnnouncementModal title={selectedAnnouncement.title} onClose={closeAnnouncementDetails}><AnnouncementDetails item={selectedAnnouncement} /></AnnouncementModal>}
  </>
}
