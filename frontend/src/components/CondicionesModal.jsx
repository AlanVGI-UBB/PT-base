import { useEffect, useState } from 'react'

const IconoX = ({ size = 18 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="18" y1="6" x2="6" y2="18"/>
    <line x1="6" y1="6" x2="18" y2="18"/>
  </svg>
)

export default function CondicionesModal({ open, onConfirm, onCancel }) {
  const [confirmado, setConfirmado] = useState(false)

  useEffect(() => {
    if (!open) setConfirmado(false)
  }, [open])

  useEffect(() => {
    if (!open) return undefined
    const handler = (e) => {
      if (e.key === 'Escape') onCancel()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [open, onCancel])

  if (!open) return null

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!confirmado) return
    onConfirm()
  }

  return (
    <div className="modal-overlay" onClick={onCancel}>
      <div className="modal" role="dialog" aria-modal="true" aria-labelledby="condiciones-titulo" onClick={(e) => e.stopPropagation()}>
        <div className="modal__header">
          <h2 id="condiciones-titulo" className="modal__title">Condiciones de registro de la sesión</h2>
          <button className="modal__close" onClick={onCancel} aria-label="Cerrar">
            <IconoX size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal__body">
            <p className="modal__descripcion">
              Antes de activar el micrófono e iniciar la captura de la clase, revisa qué se registra en esta prueba de concepto:
            </p>

            <ul className="condiciones-lista">
              <li>
                <strong>Qué se guarda:</strong> el texto transcrito y los eventos de señas detectadas. <strong>El audio no se almacena</strong> en el servidor.
              </li>
              <li>
                <strong>Quién puede consultarlo:</strong> únicamente los estudiantes inscritos en esta sección a través del historial.
              </li>
              <li>
                <strong>Conservación:</strong> aún no existe una política institucional definida de conservación o eliminación de registros.
              </li>
            </ul>

            <p className="condiciones-nota">
              Este aviso informativo no reemplaza la autorización del docente ni las normas del curso para registrar la clase.
            </p>

            <label className="condiciones-check">
              <input
                type="checkbox"
                checked={confirmado}
                onChange={(e) => setConfirmado(e.target.checked)}
              />
              <span>Confirmo que comprendo estas condiciones y cuento con autorización para iniciar la captura.</span>
            </label>
          </div>

          <div className="modal__footer">
            <button type="button" className="btn btn--ghost" onClick={onCancel}>
              Cancelar
            </button>
            <button type="submit" className="btn btn--primary" disabled={!confirmado}>
              Confirmar e iniciar
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
