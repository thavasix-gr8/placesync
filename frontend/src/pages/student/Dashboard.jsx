import { useCallback, useEffect, useState } from 'react'
import { Bell, BriefcaseBusiness, CheckCircle2, FileText, Megaphone } from 'lucide-react'
import { apiRequest } from '../../api'
import { useOutletContext } from 'react-router-dom'
import Button from '../../components/Button'
import Card from '../../components/Card'
import AnnouncementModal from '../../components/AnnouncementModal'
import EmptyState from '../../components/EmptyState'
import ProfileCompleteness from '../../components/ProfileCompleteness'
import Skeleton from '../../components/Skeleton'
import { formatDate } from '../../utils/formatters'

function AnnouncementRow({ item, onOpen }) {
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

export default function StudentDashboard() {
  const { user } = useOutletContext()
  const [stats, setStats] = useState(null)
  const [notifications, setNotifications] = useState([])
  const [announcements, setAnnouncements] = useState([])
  const [markingRead, setMarkingRead] = useState(false)
  const [updateError, setUpdateError] = useState('')
  const [resume, setResume] = useState(null)
  const [resumeLoaded, setResumeLoaded] = useState(false)
  const [showAllAnnouncements, setShowAllAnnouncements] = useState(false)
  const [selectedAnnouncement, setSelectedAnnouncement] = useState(null)
  const closeAllAnnouncements = useCallback(() => setShowAllAnnouncements(false), [])
  const closeAnnouncementDetails = useCallback(() => setSelectedAnnouncement(null), [])

  useEffect(() => {
    let active = true
    Promise.all([
      apiRequest('/drives'),
      apiRequest('/applications/me'),
      apiRequest('/notifications/me'),
      apiRequest('/announcements'),
    ]).then(([drives, applications, userNotifications, latestAnnouncements]) => {
      if (!active) return
      setStats({
        eligible: drives.filter(drive => drive.eligible).length,
        applied: applications.length,
        shortlisted: applications.filter(application => application.status === 'Shortlisted').length,
      })
      setNotifications(userNotifications)
      setAnnouncements(latestAnnouncements)
    }).catch(() => {
      if (active) {
        setStats({ eligible: 0, applied: 0, shortlisted: 0 })
        setUpdateError('Could not load notifications and announcements.')
      }
    })
    return () => { active = false }
  }, [])

  useEffect(() => {
    if (!user?.id) return
    let active = true
    apiRequest('/resumes/me').then(value => {
      if (active) setResume(value)
    }).catch(() => {
      if (active) setResume(null)
    }).finally(() => {
      if (active) setResumeLoaded(true)
    })
    return () => { active = false }
  }, [user?.id])

  async function markAllRead() {
    setMarkingRead(true)
    setUpdateError('')
    try {
      await apiRequest('/notifications/me/read', { method: 'PUT' })
      setNotifications(current => current.map(item => ({ ...item, is_read: true })))
    } catch {
      setUpdateError('Could not mark notifications as read. Please try again.')
    } finally {
      setMarkingRead(false)
    }
  }

  function openAnnouncement(item) {
    setShowAllAnnouncements(false)
    setSelectedAnnouncement(item)
  }

  function renderAnnouncementList(items) {
    return <div className="announcement-compact-list">{items.map(item => <AnnouncementRow key={item.id} item={item} onOpen={openAnnouncement} />)}</div>
  }

  if (!stats) return <Skeleton count={3} />
  const cards = [
    ['Eligible drives', stats.eligible, BriefcaseBusiness, 'cyan'],
    ['Applied', stats.applied, FileText, 'purple'],
    ['Shortlisted', stats.shortlisted, CheckCircle2, 'amber'],
  ]
  const hasUnread = notifications.some(item => !item.is_read)

  return <>
    <div className="page-heading"><div><p className="eyebrow">STUDENT DASHBOARD</p><h1>Your placement space</h1></div></div>
    <div className="stats-grid">{cards.map(([label, value, Icon, colour]) => <Card key={label} className={`stat-card ${colour}`}><Icon /><div><p>{label}</p><strong>{value}</strong></div></Card>)}</div>
    <Card className="highlight-card"><p className="eyebrow">YOUR NEXT STEP</p><h2>Check eligible drives</h2><p>The drive list checks every rule against your current profile and shows a clear reason whenever you do not qualify.</p></Card>
    {resumeLoaded && user && <Card className="profile-completeness-card"><ProfileCompleteness profile={user} hasResume={Boolean(resume)} /></Card>}
    <div className="student-updates-grid">
      <Card className="student-update-card">
        <div className="student-update-heading"><div><p className="eyebrow"><Bell size={14} /> UPDATES</p><h2>Notifications</h2></div>
          <Button type="button" variant="ghost" disabled={!hasUnread || markingRead} onClick={markAllRead}>{markingRead ? 'Saving…' : 'Mark all as read'}</Button>
        </div>
        {notifications.length === 0 ? <EmptyState title="No notifications" text="Application status updates will appear here." /> :
          <div className="student-update-list">{notifications.slice(0, 5).map(item => <div className={`notification-item ${item.is_read ? '' : 'unread'}`} key={item.id}>
            <span className="notification-dot" />
            <div><p>{item.message}</p><small>{formatDate(item.created_at)}</small></div>
          </div>)}</div>}
      </Card>
      <Card className="student-update-card">
        <div className="student-update-heading"><div><p className="eyebrow"><Megaphone size={14} /> PLACEMENT CELL</p><h2>Announcements</h2></div>
          {announcements.length > 0 && <Button type="button" variant="ghost" onClick={() => setShowAllAnnouncements(true)}>View all</Button>}
        </div>
        {announcements.length === 0 ? <EmptyState title="No announcements" text="New placement cell updates will appear here." /> :
          renderAnnouncementList(announcements.slice(0, 3))}
      </Card>
    </div>
    {updateError && <p className="student-update-error" role="alert">{updateError}</p>}
    {showAllAnnouncements && <AnnouncementModal title="All announcements" onClose={closeAllAnnouncements} className="announcement-list-modal">{renderAnnouncementList(announcements)}</AnnouncementModal>}
    {selectedAnnouncement && <AnnouncementModal title={selectedAnnouncement.title} onClose={closeAnnouncementDetails}><AnnouncementDetails item={selectedAnnouncement} /></AnnouncementModal>}
  </>
}
