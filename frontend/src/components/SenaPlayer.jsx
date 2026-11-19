import { useEffect, useRef, useState } from 'react'

const API_BASE = import.meta.env.VITE_API_URL
const API_URL = API_BASE !== undefined ? API_BASE : 'http://localhost:8000'

export default function SenaPlayer({ sena, senas, playId = 0, onEnded }) {
  const item = sena || (senas && senas[0]) || null
  const [error, setError] = useState(false)
  const onEndedRef = useRef(onEnded)
  onEndedRef.current = onEnded

  useEffect(() => {
    setError(false)
  }, [item?.video_url, playId])

  useEffect(() => {
    if (!error) return undefined
    const timer = setTimeout(() => {
      onEndedRef.current?.()
    }, 1500)
    return () => clearTimeout(timer)
  }, [error, item?.video_url, playId])

  if (!item) return null

  return (
    <div className="sena-grid">
      <div className="sena-item">
        {item.estado === 'ensayo' && (
          <span className="sena-ensayo">Clip de ensayo · sin validación lingüística</span>
        )}
        {error ? (
          <div className="sena-error">Video no disponible</div>
        ) : (
          <video
            key={`${item.video_url || 'sin-video'}-${playId}`}
            src={item.video_url ? `${API_URL}${item.video_url}` : undefined}
            autoPlay
            muted
            playsInline
            className="sena-video"
            onEnded={() => onEndedRef.current?.()}
            onError={() => setError(true)}
          />
        )}
        <span className="sena-label">{item.texto_visible}</span>
      </div>
    </div>
  )
}
