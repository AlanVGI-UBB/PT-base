import { useEffect, useRef, useState } from 'react'
import { obtenerClip } from '../api/clips'

export default function SenaPlayer({
  sena,
  senas,
  playId = 0,
  reproduciendo = true,
  velocidad = 1,
  onEnded,
}) {
  const item = sena || (senas && senas[0]) || null
  const [blobUrl, setBlobUrl] = useState(null)
  const [error, setError] = useState(false)
  const videoRef = useRef(null)
  const onEndedRef = useRef(onEnded)
  onEndedRef.current = onEnded

  useEffect(() => {
    let cancelado = false
    setError(false)
    if (!item?.video_url) {
      setBlobUrl(null)
      if (item) setError(true)
      return undefined
    }
    obtenerClip(item.video_url)
      .then((url) => {
        if (cancelado) return
        if (!url) {
          setBlobUrl(null)
          setError(true)
        } else {
          setBlobUrl(url)
        }
      })
      .catch(() => {
        if (!cancelado) {
          setBlobUrl(null)
          setError(true)
        }
      })
    return () => {
      cancelado = true
    }
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
    if (!video || error || !blobUrl) return
    video.playbackRate = velocidad
    if (reproduciendo) {
      const promesa = video.play()
      if (promesa && typeof promesa.catch === 'function') {
        promesa.catch(() => {})
      }
    } else {
      video.pause()
    }
  }, [reproduciendo, velocidad, blobUrl, playId, error])

  if (!item) return null

  return (
    <div className="sena-grid">
      <div className="sena-item">
        {item.estado === 'ensayo' && (
          <span className="sena-ensayo">Clip de ensayo · sin validación lingüística</span>
        )}
        {error ? (
          <div className="sena-error">Video no disponible</div>
        ) : blobUrl ? (
          <video
            ref={videoRef}
            key={`${item.video_url || 'sin-video'}-${playId}`}
            src={blobUrl}
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
        ) : (
          <div className="sena-error">Cargando clip...</div>
        )}
        <span className="sena-label">{item.texto_visible}</span>
      </div>
    </div>
  )
}
