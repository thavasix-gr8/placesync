import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { UserPlus } from 'lucide-react'
import { apiRequest } from '../api'
import Button from '../components/Button'

const initialForm = { name: '', email: '', password: '', register_number: '', department: 'IT', batch: '2026', cgpa: '', arrears: '0' }
export default function Signup() {
  const navigate = useNavigate(); const [form, setForm] = useState(initialForm); const [error, setError] = useState(''); const [loading, setLoading] = useState(false)
  function change(event) { setForm({ ...form, [event.target.name]: event.target.value }) }
  async function submit(event) {
    event.preventDefault(); setError(''); setLoading(true)
    try { await apiRequest('/signup', { method: 'POST', body: JSON.stringify({ ...form, cgpa: Number(form.cgpa), arrears: Number(form.arrears) }) }); navigate('/login') }
    catch (err) { setError(err.message) } finally { setLoading(false) }
  }
  return <div className="signup-page"><form className="auth-form signup-form" onSubmit={submit}><UserPlus className="form-icon" /><p className="eyebrow">STUDENT REGISTRATION</p><h2>Create your profile</h2>{error && <p className="form-error">{error}</p>}<div className="form-grid"><label>Full name<input name="name" value={form.name} onChange={change} required /></label><label>College email<input name="email" type="email" value={form.email} onChange={change} required /></label><label>Register number<input name="register_number" value={form.register_number} onChange={change} required /></label><label>Department<input name="department" value={form.department} onChange={change} required /></label><label>Batch<input name="batch" value={form.batch} onChange={change} required /></label><label>CGPA<input name="cgpa" type="number" min="0" max="10" step="0.01" value={form.cgpa} onChange={change} required /></label><label>Arrears<input name="arrears" type="number" min="0" value={form.arrears} onChange={change} required /></label><label>Password<input name="password" type="password" minLength="6" value={form.password} onChange={change} required /></label></div><Button disabled={loading}>{loading ? 'Creating...' : 'Create student account'}</Button><p className="form-footer">Already registered? <Link to="/login">Sign in</Link></p></form></div>
}
