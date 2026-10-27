import { useEffect, useRef, useState } from 'react'
import { CheckCircle2, Eye, EyeOff, FileText, Save, X } from 'lucide-react'
import { useOutletContext } from 'react-router-dom'
import { API_URL, apiRequest } from '../../api'
import Button from '../../components/Button'
import Card from '../../components/Card'
import Skeleton from '../../components/Skeleton'
import { formatDate } from '../../utils/formatters'

const MAX_RESUME_BYTES = 10 * 1024 * 1024

export default function Profile() {
  const { user, refreshUser, showToast } = useOutletContext()
  const [form, setForm] = useState(null)
  const [saving, setSaving] = useState(false)
  const [resume, setResume] = useState(null)
  const [resumeFile, setResumeFile] = useState(null)
  const [uploadingResume, setUploadingResume] = useState(false)
  const [resumeStatus, setResumeStatus] = useState(null)
  const [viewingResume, setViewingResume] = useState(false)
  const [resumeViewer, setResumeViewer] = useState(null)
  const [resumeLoaded, setResumeLoaded] = useState(false)
  const [passwordForm, setPasswordForm] = useState({ current_password: '', new_password: '', confirm_password: '' })
  const [passwordVisibility, setPasswordVisibility] = useState({ current: false, next: false, confirm: false })
  const [changingPassword, setChangingPassword] = useState(false)
  const [passwordStatus, setPasswordStatus] = useState(null)
  const resumeInput = useRef(null)
  const userId = user?.id

  useEffect(() => {
    if (user) setForm({ department: user.department, batch: user.batch, cgpa: user.cgpa, arrears: user.arrears })
  }, [user])

  useEffect(() => {
    if (userId) apiRequest('/resumes/me').then(setResume).catch(() => setResume(null)).finally(() => setResumeLoaded(true))
  }, [userId])

  useEffect(() => {
    if (!resumeViewer) return undefined
    return () => URL.revokeObjectURL(resumeViewer.url)
  }, [resumeViewer])

  if (!form) return <Skeleton count={1} />

  function change(event) {
    setForm({ ...form, [event.target.name]: event.target.value })
  }

  async function submit(event) {
    event.preventDefault()
    setSaving(true)
    try {
      await apiRequest('/me', {
        method: 'PUT',
        body: JSON.stringify({ ...form, cgpa: Number(form.cgpa), arrears: Number(form.arrears) }),
      })
      await refreshUser()
      showToast('Profile updated. Eligibility is now recalculated.')
    } catch (error) {
      showToast(error.message, 'error')
    } finally {
      setSaving(false)
    }
  }

  async function submitPasswordChange(event) {
    event.preventDefault()
    setPasswordStatus(null)
    if (passwordForm.new_password !== passwordForm.confirm_password) {
      setPasswordStatus({ type: 'error', message: 'The new passwords do not match.' })
      return
    }
    setChangingPassword(true)
    try {
      const result = await apiRequest('/me/password', {
        method: 'PUT',
        body: JSON.stringify({
          current_password: passwordForm.current_password,
          new_password: passwordForm.new_password,
        }),
      })
      setPasswordForm({ current_password: '', new_password: '', confirm_password: '' })
      setPasswordStatus({ type: 'success', message: result.message })
      showToast('Password changed successfully.')
    } catch (error) {
      setPasswordStatus({ type: 'error', message: error.message })
    } finally {
      setChangingPassword(false)
    }
  }

  function togglePassword(field) {
    setPasswordVisibility(current => ({ ...current, [field]: !current[field] }))
  }

  const completenessItems = [
    ['department', form.department, 'add your department'],
    ['batch', form.batch, 'add your batch'],
    ['CGPA', form.cgpa, 'add your CGPA'],
    ['arrears', form.arrears, 'add your arrears'],
    ['resume', Boolean(resume), 'upload a resume to finish'],
  ]
  const completedItems = completenessItems.filter(([, value]) => value !== null && value !== undefined && value !== '' && value !== false).length
  const completeness = Math.round((completedItems / completenessItems.length) * 100)
  const missingItem = completenessItems.find(([, value]) => value === null || value === undefined || value === '' || value === false)

  function selectResume(event) {
    const file = event.target.files?.[0]
    setResumeStatus(null)
    if (!file) {
      setResumeFile(null)
      return
    }
    if (!file.name.toLowerCase().endsWith('.pdf') || (file.type && file.type !== 'application/pdf')) {
      setResumeStatus({ type: 'error', message: 'Choose a PDF file.' })
      event.target.value = ''
      setResumeFile(null)
      return
    }
    if (file.size > MAX_RESUME_BYTES) {
      setResumeStatus({ type: 'error', message: 'Resume must be 10 MB or smaller.' })
      event.target.value = ''
      setResumeFile(null)
      return
    }
    setResumeFile(file)
  }

  async function uploadResume(event) {
    event.preventDefault()
    if (!resumeFile) {
      setResumeStatus({ type: 'error', message: 'Choose a PDF resume first.' })
      return
    }
    if (resumeFile.size > MAX_RESUME_BYTES) {
      setResumeStatus({ type: 'error', message: 'Resume must be 10 MB or smaller.' })
      return
    }

    const body = new FormData()
    body.append('file', resumeFile)
    setUploadingResume(true)
    setResumeStatus({ type: 'info', message: 'Uploading resume…' })
    try {
      const uploaded = await apiRequest('/resumes/me', { method: 'POST', body })
      setResume(uploaded)
      setResumeFile(null)
      if (resumeInput.current) resumeInput.current.value = ''
      setResumeStatus({ type: 'success', message: 'Resume uploaded successfully.' })
      showToast('Resume uploaded successfully.')
    } catch (error) {
      setResumeStatus({ type: 'error', message: error.message })
      showToast(error.message, 'error')
    } finally {
      setUploadingResume(false)
    }
  }

  async function viewResume() {
    setViewingResume(true)
    setResumeStatus(null)
    try {
      const response = await fetch(`${API_URL}/resumes/me/view`, {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
      })
      if (!response.ok) {
        const body = await response.json().catch(() => null)
        throw new Error(body?.detail || 'Could not open your resume.')
      }
      const blob = await response.blob()
      setResumeViewer({ url: URL.createObjectURL(blob), filename: resume?.filename || 'Resume' })
    } catch (error) {
      setResumeStatus({ type: 'error', message: error.message })
      showToast(error.message, 'error')
    } finally {
      setViewingResume(false)
    }
  }

  return <div className="student-profile-page">
    <div className="page-heading">
      <div>
        <p className="eyebrow">STUDENT PROFILE</p>
        <h1>Keep your details current</h1>
        <p>Your CGPA, arrears, department and batch decide drive eligibility.</p>
      </div>
    </div>
    <div className="student-profile-cards">
    <Card className="profile-card">
      <div className="profile-name">
        <h2>{user.name}</h2>
        <p>{user.email} · {user.register_number}</p>
      </div>
      {resumeLoaded && <div className="profile-completeness profile-completeness-profile">
        <div className="profile-completeness-heading">
          <strong>{completeness === 100 ? <><CheckCircle2 size={16} /> Profile complete</> : `Profile ${completeness}% done: ${missingItem?.[2]}.`}</strong>
          <span>{completeness}%</span>
        </div>
        <div className="profile-progress-track" role="progressbar" aria-valuenow={completeness} aria-valuemin="0" aria-valuemax="100" aria-label={`Profile ${completeness}% complete`}>
          <span style={{ width: `${completeness}%` }} />
        </div>
      </div>}
      <form onSubmit={submit} className="form-grid profile-details-form">
        <label>Department<input name="department" value={form.department} onChange={change} required /></label>
        <label>Batch<input name="batch" value={form.batch} onChange={change} required /></label>
        <label>CGPA<input name="cgpa" type="number" min="0" max="10" step="0.01" value={form.cgpa} onChange={change} required /></label>
        <label>Arrears<input name="arrears" type="number" min="0" value={form.arrears} onChange={change} required /></label>
        <Button className="profile-save-button" disabled={saving}>{saving ? 'Saving...' : <><Save size={16} /> Save profile</>}</Button>
      </form>
    </Card>
    <Card className="profile-card password-change-card">
      <h2>Change password</h2>
      <form className="form-grid password-change-form" onSubmit={submitPasswordChange}>
        {[
          ['current_password', 'Current password', 'current'],
          ['new_password', 'New password', 'next'],
          ['confirm_password', 'Confirm new password', 'confirm'],
        ].map(([field, label, visibilityKey]) => <label key={field}>{label}
          <span className="password-input-wrap">
            <input
              type={passwordVisibility[visibilityKey] ? 'text' : 'password'}
              value={passwordForm[field]}
              onChange={event => setPasswordForm(current => ({ ...current, [field]: event.target.value }))}
              minLength={field === 'current_password' ? undefined : 8}
              required
            />
            <button className="password-toggle" type="button" aria-label={`${passwordVisibility[visibilityKey] ? 'Hide' : 'Show'} password`} onClick={() => togglePassword(visibilityKey)}>
              {passwordVisibility[visibilityKey] ? <EyeOff size={17} /> : <Eye size={17} />}
            </button>
          </span>
        </label>)}
        <Button className="password-change-submit" disabled={changingPassword}>{changingPassword ? 'Changing…' : 'Change password'}</Button>
      </form>
      {passwordStatus && <p className={`password-change-status ${passwordStatus.type}`} role={passwordStatus.type === 'error' ? 'alert' : 'status'}>{passwordStatus.message}</p>}
    </Card>
    <Card className="profile-card resume-card">
      <div className="resume-card-heading">
        <h2>Resume</h2>
        <p>Upload a PDF up to 10 MB. Your resume is attached to each new application.</p>
      </div>
      {resume ? <div className="resume-current-row">
        <FileText size={20} aria-hidden="true" />
        <div className="resume-current-details">
          <strong>{resume.filename}</strong>
          <span>Uploaded {formatDate(resume.uploaded_at)}</span>
        </div>
        <Button type="button" variant="ghost" disabled={viewingResume} onClick={viewResume}>
          <Eye size={16} /> {viewingResume ? 'Opening…' : 'View resume'}
        </Button>
      </div> : <p className="resume-empty">No resume uploaded yet.</p>}
      <form className="resume-upload-row" onSubmit={uploadResume}>
        <input ref={resumeInput} className="resume-file-input" id="resume-file" type="file" accept="application/pdf,.pdf" onChange={selectResume} />
        <Button type="button" variant="ghost" onClick={() => resumeInput.current?.click()}>
          Choose PDF
        </Button>
        <span className="resume-selected-name" title={resumeFile?.name || ''}>
          {resumeFile?.name || 'No file selected'}
        </span>
        <Button disabled={uploadingResume}>
          {uploadingResume ? 'Uploading…' : resume ? 'Replace resume' : 'Upload'}
        </Button>
      </form>
      {resumeStatus && <p className={`resume-upload-status ${resumeStatus.type}`} role={resumeStatus.type === 'error' ? 'alert' : 'status'}>{resumeStatus.message}</p>}
    </Card>
    </div>
    {resumeViewer && <div className="resume-preview-overlay" role="presentation" onClick={() => setResumeViewer(null)}>
      <section className="resume-preview-modal" role="dialog" aria-modal="true" aria-label={`${resumeViewer.filename} preview`} onClick={event => event.stopPropagation()}>
        <div className="resume-preview-header">
          <strong>{resumeViewer.filename}</strong>
          <button className="icon-button" type="button" aria-label="Close resume preview" onClick={() => setResumeViewer(null)}><X size={18} /></button>
        </div>
        <iframe title="Resume preview" src={resumeViewer.url} />
      </section>
    </div>}
  </div>
}
