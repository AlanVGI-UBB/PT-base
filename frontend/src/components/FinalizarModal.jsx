import { useEffect, useRef, useState } from 'react'

const IconoX = ({ size = 18 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="18" y1="6" x2="6" y2="18"/>
    <line x1="6" y1="6" x2="18" y2="18"/>
  </svg>
)

const IconoGuardar = ({ size = 18 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>
    <polyline points="17 21 17 13 7 13 7 21"/>
    <polyline points="7 3 7 8 15 8"/>
  </svg>
)

export default function FinalizarModal({ open, onConfirm, onCancel }) {
  const [titulo, setTitulo] = useState('')
  const inputRef = useRef(null)

  useEffect(() => {
    if (open && inputRef.current) {
      setTimeout(() => inputRef.current?.focus(), 100)
    }
    if (!open) setTitulo('')
  }, [open])

  useEffect(() => {
    if (!open) return
    const handler = (e) => {
      if (e.key === 'Escape') onCancel()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [open, onCancel])

  if (!open) return null

  const handleSubmit = (e) => {
    e.preventDefault()
    onConfirm(titulo.trim() || null)
  }

  return (
    <div className="modal-overlay" onClick={onCancel}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal__header">
          <h2 className="modal__title">¿Finalizar Sesión?</h2>
          <button className="modal__close" onClick={onCancel} aria-label="Cerrar">
            <IconoX size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal__body">
            <p className="modal__descripcion">
              Estás a punto de finalizar la clase actual. Por favor, asigna un
              título o nota para guardar el registro de la sesión en tu historial.
            </p>

            <label className="modal__campo">
              <span>Título/Nota de la sesión</span>
              <input
                ref={inputRef}
                type="text"
                value={titulo}
                onChange={(e) => setTitulo(e.target.value)}
                placeholder="ej. Algoritmos de ordenamiento"
                maxLength={120}
                autoFocus
              />
            </label>
          </div>

          <div className="modal__footer">
            <button type="button" className="btn btn--ghost" onClick={onCancel}>
              <IconoX size={16} /> Cancelar
            </button>
            <button type="submit" className="btn btn--primary">
              <IconoGuardar size={16} /> Guardar y Salir
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
