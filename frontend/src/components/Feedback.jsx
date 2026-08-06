export default function Feedback({ tipo = 'error', mensaje, onClose }) {
  if (!mensaje) return null
  return (
    <div className={`feedback feedback--${tipo}`} role="alert">
      <span className="feedback__mensaje">{mensaje}</span>
      {onClose && (
        <button className="feedback__cerrar" onClick={onClose} aria-label="Cerrar aviso">
          ×
        </button>
      )}
    </div>
  )
}
