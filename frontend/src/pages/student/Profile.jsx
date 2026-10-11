import { useEffect, useState } from 'react'
import { Save } from 'lucide-react'
import { useOutletContext } from 'react-router-dom'
import { apiRequest } from '../../api'
import Button from '../../components/Button'
import Card from '../../components/Card'
import Skeleton from '../../components/Skeleton'

export default function Profile() {
  const { user, refreshUser, showToast } = useOutletContext(); const [form, setForm] = useState(null); const [saving, setSaving] = useState(false)
  useEffect(() => { if (user) setForm({ department: user.department, batch: user.batch, cgpa: user.cgpa, arrears: user.arrears }) }, [user])
  if (!form) return <Skeleton count={1} />
  function change(e) { setForm({ ...form, [e.target.name]: e.target.value }) }
  async function submit(e) { e.preventDefault(); setSaving(true); try { await apiRequest('/me', { method: 'PUT', body: JSON.stringify({ ...form, cgpa: Number(form.cgpa), arrears: Number(form.arrears) }) }); await refreshUser(); showToast('Profile updated. Eligibility is now recalculated.'); } catch (err) { showToast(err.message, 'error') } finally { setSaving(false) } }
  return <><div className="page-heading"><div><p className="eyebrow">STUDENT PROFILE</p><h1>Keep your details current</h1><p>Your CGPA, arrears, department and batch decide drive eligibility.</p></div></div><Card className="profile-card"><div className="profile-name"><h2>{user.name}</h2><p>{user.email} · {user.register_number}</p></div><form onSubmit={submit} className="form-grid"><label>Department<input name="department" value={form.department} onChange={change} required /></label><label>Batch<input name="batch" value={form.batch} onChange={change} required /></label><label>CGPA<input name="cgpa" type="number" min="0" max="10" step="0.01" value={form.cgpa} onChange={change} required /></label><label>Arrears<input name="arrears" type="number" min="0" value={form.arrears} onChange={change} required /></label><Button disabled={saving}>{saving ? 'Saving...' : <><Save size={16} /> Save profile</>}</Button></form></Card></>
}
