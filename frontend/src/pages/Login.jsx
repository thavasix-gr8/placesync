import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ArrowRight, BadgeCheck, ClipboardCheck, Eye, EyeOff, Route } from 'lucide-react'
import { apiRequest } from '../api'
import {
  initialiseMicrosoftAuth,
  microsoftErrorMessage,
  signInWithMicrosoft,
  takeMicrosoftRedirectResult,
} from '../microsoftAuth'
import Button from '../components/Button'

async function microsoftRequest(path, options = {}) {
  const controller = new AbortController()
  const timeout = window.setTimeout(() => controller.abort(), 10000)
  try {
    return await apiRequest(path, { ...options, signal: controller.signal })
  } catch (error) {
    if (controller.signal.aborted) {
      throw new Error('The PlaceSync sign-in service timed out. Please retry.')
    }
    throw error
  } finally {
    window.clearTimeout(timeout)
  }
}

function logMicrosoftError(error) {
  const code = error?.errorCode || error?.code || (error?.status ? `http_${error.status}` : error?.name)
  console.warn('[PlaceSync Microsoft sign-in]', code || 'unknown_error')
}

export default function Login() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [microsoftBusy, setMicrosoftBusy] = useState(false)
  const [pendingMicrosoftToken, setPendingMicrosoftToken] = useState('')
  const microsoftAttempt = useRef(false)

  const finishMicrosoftSignIn = useCallback(async idToken => {
    setError('')
    setMicrosoftBusy(true)
    try {
      const session = await microsoftRequest('/auth/microsoft/login', {
        method: 'POST', body: JSON.stringify({ id_token: idToken }),
      })
      localStorage.setItem('token', session.access_token)
      localStorage.setItem('role', session.role)
      navigate('/student/dashboard')
    } catch (authError) {
      logMicrosoftError(authError)
      if (authError.status === 409) {
        setPendingMicrosoftToken(idToken)
        setError('This Microsoft account is not linked yet. Sign in below with your PlaceSync student email and password to link it safely.')
      } else setError(microsoftErrorMessage(authError))
    } finally { setMicrosoftBusy(false) }
  }, [navigate])

  useEffect(() => {
    let active = true
    initialiseMicrosoftAuth()
      .then(async () => {
        if (!active) return
        const result = await takeMicrosoftRedirectResult()
        if (active && result?.idToken) await finishMicrosoftSignIn(result.idToken)
      })
      .catch(authError => {
        if (!active) return
        logMicrosoftError(authError)
        setError(microsoftErrorMessage(authError))
      })
    return () => { active = false }
  }, [finishMicrosoftSignIn])

  async function submit(event) {
    event.preventDefault()
    setError(''); setLoading(true)
    try {
      const data = await apiRequest('/login', { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: new URLSearchParams({ username: email, password }) })
      const session = pendingMicrosoftToken
        ? await microsoftRequest('/auth/microsoft/link', {
          method: 'POST',
          headers: { Authorization: `Bearer ${data.access_token}` },
          body: JSON.stringify({ id_token: pendingMicrosoftToken }),
        })
        : data
      localStorage.setItem('token', session.access_token)
      localStorage.setItem('role', session.role)
      navigate(session.role === 'admin' ? '/admin/dashboard' : '/student/dashboard')
    } catch (err) {
      setError(err.message)
      if (pendingMicrosoftToken) setPendingMicrosoftToken('')
    } finally { setLoading(false) }
  }

  async function microsoftSignIn() {
    if (microsoftAttempt.current) return
    microsoftAttempt.current = true
    setError(''); setMicrosoftBusy(true)
    try {
      const data = await microsoftRequest('/auth/microsoft/nonce', { method: 'POST' })
      await signInWithMicrosoft(data.nonce)
    } catch (authError) {
      logMicrosoftError(authError)
      setError(microsoftErrorMessage(authError))
    } finally {
      microsoftAttempt.current = false
      setMicrosoftBusy(false)
    }
  }

  return <div className="auth-page">
    <aside className="auth-brand">
      <div className="brand-copy">
        <p className="eyebrow campus-label">SSN COLLEGE OF ENGINEERING · CHENNAI</p>
        <div className="ssn-wordmark">SSN</div>
        <h1>Placements at SSN, <span>simplified.</span></h1>
        <div className="brand-chips">
          <span><BadgeCheck /> Know why you&apos;re eligible</span>
          <span><ClipboardCheck /> Apply in one click</span>
          <span><Route /> Track every round</span>
        </div>
      </div>
      <p className="brand-footer">Built by B.Tech IT students, SSN</p>
    </aside>
    <main className="auth-form-wrap"><form className="auth-form" onSubmit={submit}><p className="eyebrow">WELCOME BACK</p><h2>Sign in to PlaceSync</h2><p className="muted">Use your college placement account.</p>{error && <p className="form-error">{error}</p>}<label>Email<input type="email" value={email} onChange={e => setEmail(e.target.value)} required /></label><label>Password<span className="password-input-wrap"><input type={showPassword ? 'text' : 'password'} value={password} onChange={e => setPassword(e.target.value)} required /><button className="password-toggle" type="button" aria-label={showPassword ? 'Hide password' : 'Show password'} aria-pressed={showPassword} onClick={() => setShowPassword(!showPassword)}>{showPassword ? <EyeOff size={18} /> : <Eye size={18} />}</button></span></label><Button disabled={loading}>{loading ? 'Signing in...' : pendingMicrosoftToken ? <>Link Microsoft account <ArrowRight size={17} /></> : <>Sign in <ArrowRight size={17} /></>}</Button><div className="auth-divider"><span>OR</span></div><Button type="button" variant="ghost" disabled={loading || microsoftBusy} onClick={microsoftSignIn}>{microsoftBusy ? 'Connecting to Microsoft...' : 'Continue with Microsoft'}</Button><p className="form-footer">New student? <Link to="/signup">Create an account</Link></p><p className="demo-note">Demo admin: admin@placesync.com / admin123</p></form></main>
  </div>
}
