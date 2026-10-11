import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ArrowRight, BriefcaseBusiness, ShieldCheck } from 'lucide-react'
import { apiRequest } from '../api'
import Button from '../components/Button'

export default function Login() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function submit(event) {
    event.preventDefault()
    setError(''); setLoading(true)
    try {
      const data = await apiRequest('/login', { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: new URLSearchParams({ username: email, password }) })
      localStorage.setItem('token', data.access_token)
      localStorage.setItem('role', data.role)
      navigate(data.role === 'admin' ? '/admin/dashboard' : '/student/dashboard')
    } catch (err) { setError(err.message) } finally { setLoading(false) }
  }

  return <div className="auth-page">
    <aside className="auth-brand"><BriefcaseBusiness size={48} /><p className="eyebrow">PLACEMENT, SIMPLIFIED</p><h1>Find the right <span>opportunity.</span></h1><p>One place for placements, applications and transparent eligibility checks.</p><div className="feature-line"><ShieldCheck /> See exactly why a drive matches your profile.</div></aside>
    <main className="auth-form-wrap"><form className="auth-form" onSubmit={submit}><p className="eyebrow">WELCOME BACK</p><h2>Sign in to PlaceSync</h2><p className="muted">Use your college placement account.</p>{error && <p className="form-error">{error}</p>}<label>Email<input type="email" value={email} onChange={e => setEmail(e.target.value)} required /></label><label>Password<input type="password" value={password} onChange={e => setPassword(e.target.value)} required /></label><Button disabled={loading}>{loading ? 'Signing in...' : <>Sign in <ArrowRight size={17} /></>}</Button><p className="form-footer">New student? <Link to="/signup">Create an account</Link></p><p className="demo-note">Demo admin: admin@placesync.com / admin123</p></form></main>
  </div>
}
