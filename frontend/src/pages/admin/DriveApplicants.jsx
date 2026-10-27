import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useOutletContext } from 'react-router-dom'
import { Search, Users } from 'lucide-react'
import { apiRequest } from '../../api'
import Card from '../../components/Card'
import EmptyState from '../../components/EmptyState'
import Skeleton from '../../components/Skeleton'
import { formatDate } from '../../utils/formatters'

export default function DriveApplicants() {
  const { showToast } = useOutletContext()
  const showToastRef = useRef(showToast)
  showToastRef.current = showToast
  const [drives, setDrives] = useState(null)
  const [search, setSearch] = useState('')

  useEffect(() => {
    let active = true
    apiRequest('/drives')
      .then(data => { if (active) setDrives(data) })
      .catch(() => {
        if (active) {
          setDrives([])
          showToastRef.current('Could not load drives.', 'error')
        }
      })
    return () => { active = false }
  }, [])

  const filteredDrives = useMemo(() => {
    if (!drives) return []
    const query = search.trim().toLowerCase()
    return drives.filter(drive => drive.company.toLowerCase().includes(query))
  }, [drives, search])

  return <>
    <div className="page-heading">
      <div>
        <p className="eyebrow">APPLICANT MANAGEMENT</p>
        <h1>Applicants</h1>
        <p>Choose a placement drive to review its applicants.</p>
      </div>
    </div>
    <label className="admin-applicant-search">
      <span>Search company</span>
      <div className="admin-applicant-search-input">
        <Search size={17} aria-hidden="true" />
        <input
          type="search"
          value={search}
          onChange={event => setSearch(event.target.value)}
          placeholder="Type a company name"
        />
      </div>
    </label>
    {!drives ? <Skeleton count={3} /> : drives.length === 0 ?
      <EmptyState title="No drives yet" text="Placement drives will appear here once they are created." /> :
      filteredDrives.length === 0 ?
        <EmptyState title="No matching drives" text="Try a different company name." /> :
        <div className="admin-drive-list">
          {filteredDrives.map(drive => <Card key={drive.id} className="admin-drive-card">
            <div>
              <h3>{drive.company}</h3>
              <p>{drive.job_role}</p>
              <small>Deadline {formatDate(drive.deadline)} · Applicants {drive.applicant_count}</small>
            </div>
            <Link className="button button-ghost" to={`/admin/drives/${drive.id}/applicants`}>
              <Users size={16} /> View applicants
            </Link>
          </Card>)}
        </div>}
  </>
}
