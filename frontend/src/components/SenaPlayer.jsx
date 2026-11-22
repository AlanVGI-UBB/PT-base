import { useEffect, useRef, useState } from 'react'

const API_BASE = import.meta.env.VITE_API_URL
const API_URL = API_BASE !== undefined ? API_BASE : 'http://localhost:8000'

export default function SenaPlayer({
  sena,
  senas,
  playId = 0,
  reproduciendo = true,
  velocidad = 1,
  onEnded,
}) {
  const item = sena || (senas && senas[0]) || null
  const [error, setError] = useState(false)
  const videoRef = useRef(null)
  const onEndedRef = useRef(onEnded)
  onEndedRef.current = onEnded

  useEffect(() => {
    setError(false)
  }, [item?.video_url, playId])

  useEffect(() => {
    if (!error || !reproduciendo) return undefined
    const timer = setTimeout(() => {
      onEndedRef.current?.()
    }, Math.round(1500 / velocidad))
    return () => clearTimeout(timer)
  }, [error, reproduciendo, velocidad, item?.video_url, playId])

  useEffect(() => {
    const video = videoRef.current
    if (!video || error) return
    video.playbackRate = velocidad
    if (reproduciendo) {
      const promesa = video.play()
      if (promesa && typeof promesa.catch === 'function') {
        promesa.catch(() => {})
      }
    } else {
      video.pause()
    }
  }, [reproduciendo, velocidad, item?.video_url, playId, error])

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
            ref={videoRef}
            key={`${item.video_url || 'sin-video'}-${playId}`}
            src={item.video_url ? `${API_URL}${item.video_url}` : undefined}
            autoPlay={reproduciendo}
            preload="auto"
            muted
            playsInline
            className="sena-video"
            onLoadedMetadata={(e) => {
              e.currentTarget.playbackRate = velocidad
            }}
            onEnded={() => onEndedRef.current?.()}
            onError={() => setError(true)}
          />
        )}
        <span className="sena-label">{item.texto_visible}</span>
      </div>
    </div>
  )
}
