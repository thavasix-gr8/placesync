import { useEffect, useState } from 'react'
import { Link, useOutletContext } from 'react-router-dom'
import { Edit3, PlusCircle, Trash2, Users } from 'lucide-react'
import { apiRequest } from '../../api'
import Button from '../../components/Button'
import Card from '../../components/Card'
import EmptyState from '../../components/EmptyState'
import Skeleton from '../../components/Skeleton'
import { formatDate } from '../../utils/formatters'

const blankDrive = { company: '', job_role: '', description: '', deadline: '', min_cgpa: '6', max_arrears: '0', allowed_departments: '', batch: '' }

export default function AdminDrives() {
  const { showToast } = useOutletContext()
  const [drives, setDrives] = useState(null)
  const [form, setForm] = useState(blankDrive)
  const [editingId, setEditingId] = useState(null)
  const [saving, setSaving] = useState(false)

  function load() { apiRequest('/drives').then(setDrives).catch(() => { setDrives([]); showToast('Could not load drives.', 'error') }) }
  useEffect(load, [])
  function change(event) { setForm({ ...form, [event.target.name]: event.target.value }) }
  function startEdit(drive) {
    setEditingId(drive.id)
    setForm({ ...drive, deadline: drive.deadline.slice(0, 16), min_cgpa: String(drive.min_cgpa), max_arrears: String(drive.max_arrears) })
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }
  function cancelEdit() { setEditingId(null); setForm(blankDrive) }
  async function submit(event) {
    event.preventDefault(); setSaving(true)
    const data = { ...form, deadline: new Date(form.deadline).toISOString(), min_cgpa: Number(form.min_cgpa), max_arrears: Number(form.max_arrears) }
    try {
      await apiRequest(editingId ? `/drives/${editingId}` : '/drives', { method: editingId ? 'PUT' : 'POST', body: JSON.stringify(data) })
      showToast(editingId ? 'Drive updated.' : 'Drive created.')
      cancelEdit(); load()
    } catch (err) { showToast(err.message, 'error') } finally { setSaving(false) }
  }
  async function removeDrive(id) {
    if (!window.confirm('Delete this drive and its applications?')) return
    try { await apiRequest(`/drives/${id}`, { method: 'DELETE' }); showToast('Drive deleted.'); load() } catch (err) { showToast(err.message, 'error') }
  }

  return <><div className="page-heading"><div><p className="eyebrow">DRIVE MANAGEMENT</p><h1>{editingId ? 'Edit drive' : 'Create a drive'}</h1><p>Set the eligibility rules clearly so students get the right result.</p></div></div><Card className="drive-form-card"><form onSubmit={submit}><div className="form-grid"><label>Company<input name="company" value={form.company} onChange={change} required /></label><label>Job role<input name="job_role" value={form.job_role} onChange={change} required /></label><label className="full-width">Description<textarea name="description" value={form.description} onChange={change} required /></label><label>Application deadline<input name="deadline" type="datetime-local" value={form.deadline} onChange={change} required /></label><label>Allowed departments<input name="allowed_departments" value={form.allowed_departments} onChange={change} placeholder="IT,CSE (blank means all)" /></label></div><div className="eligibility-fields"><div><p className="eyebrow">ELIGIBILITY RULES</p><h3>Automatic checks for students</h3></div><div className="form-grid compact"><label>Minimum CGPA<input name="min_cgpa" type="number" min="0" max="10" step="0.1" value={form.min_cgpa} onChange={change} required /></label><label>Maximum arrears<input name="max_arrears" type="number" min="0" value={form.max_arrears} onChange={change} required /></label><label>Batch<input name="batch" value={form.batch} onChange={change} placeholder="2026 (blank means all)" /></label></div></div><div className="form-actions"><Button disabled={saving}>{saving ? 'Saving...' : <><PlusCircle size={16} /> {editingId ? 'Update drive' : 'Create drive'}</>}</Button>{editingId && <Button type="button" variant="ghost" onClick={cancelEdit}>Cancel</Button>}</div></form></Card><div className="section-heading"><div><p className="eyebrow">POSTED DRIVES</p><h2>Manage existing drives</h2></div></div>{!drives ? <Skeleton count={3} /> : drives.length === 0 ? <EmptyState title="No drives yet" text="Use the form above to create your first drive." /> : <div className="admin-drive-list">{drives.map(drive => <Card key={drive.id} className="admin-drive-card"><div><h3>{drive.company}</h3><p>{drive.job_role} · Deadline {formatDate(drive.deadline)}</p><small>CGPA {drive.min_cgpa}+ · {drive.max_arrears} arrears · {drive.allowed_departments || 'All departments'}</small></div><div className="row-actions"><Link className="button button-ghost" to={`/admin/drives/${drive.id}/applicants`}><Users size={16} /> Applicants</Link><button className="icon-button" title="Edit drive" onClick={() => startEdit(drive)}><Edit3 size={17} /></button><button className="icon-button danger" title="Delete drive" onClick={() => removeDrive(drive.id)}><Trash2 size={17} /></button></div></Card>)}</div>}</>
}
