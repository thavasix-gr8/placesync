import { useEffect, useState } from 'react'
import { Building2, CalendarDays, CircleAlert, GraduationCap, Landmark, Search, Send, X } from 'lucide-react'
import { apiRequest } from '../../api'
import Badge from '../../components/Badge'
import Button from '../../components/Button'
import Card from '../../components/Card'
import EmptyState from '../../components/EmptyState'
import Skeleton from '../../components/Skeleton'
import { formatDate } from '../../utils/formatters'
import { useOutletContext } from 'react-router-dom'

function normaliseSearch(value) {
  return String(value || '').trim().replace(/\s+/g, ' ').toLowerCase()
}

function closesWithinSevenDays(deadline) {
  const driveDay = new Date(deadline)
  if (Number.isNaN(driveDay.getTime())) return false
  driveDay.setHours(0, 0, 0, 0)
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const daysLeft = (driveDay - today) / (24 * 60 * 60 * 1000)
  return daysLeft >= 0 && daysLeft <= 7
}

export default function StudentDrives() {
  const { showToast } = useOutletContext()
  const [drives, setDrives] = useState(null)
  const [applying, setApplying] = useState(null)
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState('all')

  function load() {
    apiRequest('/drives').then(setDrives).catch(() => {
      setDrives([])
      showToast('Could not load drives.', 'error')
    })
  }

  useEffect(load, [])

  async function apply(drive) {
    setApplying(drive.id)
    try {
      await apiRequest(`/drives/${drive.id}/apply`, { method: 'POST' })
      showToast(`Application sent to ${drive.company}`)
      load()
    } catch (error) {
      showToast(error.message, 'error')
    } finally {
      setApplying(null)
    }
  }

  if (!drives) return <Skeleton count={4} />

  const shownDrives = drives.filter(drive => {
    const matchesSearch = normaliseSearch(`${drive.company} ${drive.job_role}`).includes(normaliseSearch(search))
    let matchesFilter = true
    if (filter === 'eligible') matchesFilter = drive.eligible
    if (filter === 'closing') matchesFilter = !drive.application_closed && closesWithinSevenDays(drive.deadline)
    if (filter === 'passed') matchesFilter = drive.application_closed
    return matchesSearch && matchesFilter
  })

  function clearFilters() {
    setSearch('')
    setFilter('all')
  }

  const filterOptions = [
    ['all', 'All drives'],
    ['eligible', 'Eligible only'],
    ['closing', 'Closing in 7 days'],
    ['passed', 'Deadline passed'],
  ]

  return <div className="student-drives-page">
    <div className="page-heading drive-page-heading"><div><p className="eyebrow">ELIGIBILITY ENGINE</p><h1>Placement drives</h1><p>Every drive is checked against your saved profile.</p></div></div>
    <Card className="drive-filter-toolbar">
      <label className="drive-search">
        <span className="sr-only">Search company or role</span>
        <Search className="drive-search-icon" size={17} aria-hidden="true" />
        <input value={search} onChange={event => setSearch(event.target.value)} placeholder="Search company or role" aria-label="Search company or role" />
        {search && <button className="icon-button drive-search-clear" type="button" aria-label="Clear search" onClick={() => setSearch('')}><X size={15} /></button>}
      </label>
      <div className="drive-filter-options">
        <div className="drive-filter-chips" role="group" aria-label="Filter drives">
          {filterOptions.map(([value, label]) => <button
            key={value}
            className={`drive-filter-chip ${filter === value ? 'active' : ''}`}
            type="button"
            aria-pressed={filter === value}
            onClick={() => setFilter(value)}
          >{label}</button>)}
        </div>
        <p className="drive-result-count">Showing {shownDrives.length} of {drives.length} drives</p>
      </div>
    </Card>
    {drives.length === 0 ? <EmptyState title="No drives yet" text="Your placement team has not posted any drives." /> : shownDrives.length === 0 ?
      <div className="drive-filter-empty"><EmptyState title="No drives match your filters" text="Try a different company, role or filter." /><Button type="button" variant="ghost" onClick={clearFilters}>Clear filters</Button></div> :
      <div className="drive-grid student-drive-grid">{shownDrives.map(drive => {
        const otherReasons = (drive.reasons || []).filter(reason => reason !== 'Applications closed')
        return <Card key={drive.id} className={`drive-card ${!drive.eligible ? 'not-eligible' : ''}`}>
          <div className="card-top"><div className="company-mark"><Building2 /></div><Badge status={drive.eligible ? 'Eligible' : 'Not eligible'}>{drive.eligible ? 'Eligible' : 'Not eligible'}</Badge></div>
          <h2>{drive.company}</h2><p className="role">{drive.job_role}</p><p className="muted drive-description">{drive.description}</p>
          <div className="drive-meta"><span><CalendarDays />Deadline: {formatDate(drive.deadline)}</span></div>
          <div className="rule-chips"><span><GraduationCap />CGPA {drive.min_cgpa}+</span><span><CircleAlert />Max {drive.max_arrears} arrears</span><span><Landmark />{drive.allowed_departments || 'All departments'}</span></div>
          {drive.eligible ? <Button onClick={() => apply(drive)} disabled={applying === drive.id}>{applying === drive.id ? 'Applying...' : <><Send size={16} /> Apply now</>}</Button> : <div className="drive-card-actions">
            {drive.application_closed && <Button className="applications-closed-button" disabled>Applications closed</Button>}
            {otherReasons.length > 0 && <div className="reason-box"><strong>Why you are not eligible</strong>{otherReasons.map(reason => <p key={reason}>{reason}</p>)}</div>}
          </div>}
        </Card>
      })}</div>}
  </div>
}
