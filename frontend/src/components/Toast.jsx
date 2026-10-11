import { CheckCircle2, XCircle } from 'lucide-react'

export default function Toast({ toast, onClose }) {
  if (!toast) return null
  const Icon = toast.type === 'error' ? XCircle : CheckCircle2
  return <button className={`toast ${toast.type || 'success'}`} onClick={onClose}><Icon size={18} />{toast.message}</button>
}
