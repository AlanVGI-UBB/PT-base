import { useState } from 'react'

const API_BASE = import.meta.env.VITE_API_URL
const API_URL = API_BASE !== undefined ? API_BASE : 'http://localhost:8000'

export default function SenaPlayer({ senas }) {
  const [errores, setErrores] = useState({})
  if (!senas || senas.length === 0) return null

  return (
    <div className="sena-grid">
      {senas.map((s, i) => (
        <div key={i} className="sena-item">
          {errores[i] ? (
            <div className="sena-error">Video no disponible</div>
          ) : (
            <video
              src={s.video_url ? `${API_URL}${s.video_url}` : undefined}
              autoPlay
              muted
              loop
              playsInline
              className="sena-video"
              onError={() => setErrores((prev) => ({ ...prev, [i]: true }))}
            />
          )}
          <span className="sena-label">{s.texto_visible}</span>
        </div>
      ))}
    </div>
  )
}
