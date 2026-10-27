import { useEffect } from 'react'
import { X } from 'lucide-react'

export default function AnnouncementModal({ title, onClose, children, className = '' }) {
  useEffect(() => {
    const oldOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    function closeOnEscape(event) {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', closeOnEscape)
    return () => {
      document.body.style.overflow = oldOverflow
      window.removeEventListener('keydown', closeOnEscape)
    }
  }, [onClose])

  return <div className="announcement-modal-backdrop" onMouseDown={event => {
    if (event.target === event.currentTarget) onClose()
  }}>
    <section className={`announcement-modal ${className}`} role="dialog" aria-modal="true" aria-labelledby="announcement-modal-title">
      <header className="announcement-modal-header">
        <h2 id="announcement-modal-title">{title}</h2>
        <button className="icon-button" type="button" aria-label="Close dialog" onClick={onClose}><X size={18} /></button>
      </header>
      <div className="announcement-modal-body">{children}</div>
    </section>
  </div>
}
