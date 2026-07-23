import { useEffect, useRef, useState } from 'react'
import SenaPlayer from './SenaPlayer'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export default function ReplayPlayer({ eventos }) {
  const [pos, setPos] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [velocidad, setVelocidad] = useState(1)
  const timerRef = useRef(null)

  const estables = eventos.filter((e) => e.estable || e.texto)

  useEffect(() => {
    if (!playing || estables.length === 0) {
      clearInterval(timerRef.current)
      return
    }
    timerRef.current = setInterval(() => {
      setPos((p) => {
        if (p >= estables.length - 1) {
          setPlaying(false)
          return p
        }
        return p + 1
      })
    }, (estables[pos + 1]?.timestamp_ms - estables[pos]?.timestamp_ms) / velocidad || 500)
    return () => clearInterval(timerRef.current)
  }, [playing, pos, velocidad, estables])

  if (estables.length === 0) {
    return <p className="dashboard__vacio">No hay eventos para reproducir.</p>
  }

  const current = estables[pos]
  const senasActuales = current
    ? (typeof current.senas === 'string' ? JSON.parse(current.senas) : (current.senas || []))
    : []

  return (
    <div className="replay">
      <div className="replay__controles">
        <button className="btn btn--profesor" onClick={() => setPlaying(!playing)}>
          {playing ? 'Pausa' : 'Play'}
        </button>
        {[1, 1.5, 2].map((v) => (
          <button
            key={v}
            className={`btn ${velocidad === v ? 'btn--profesor' : 'btn--fuente'}`}
            onClick={() => setVelocidad(v)}
          >
            {v}x
          </button>
        ))}
        <div className="replay__progreso-wrapper">
          <input
            type="range"
            min={0}
            max={estables.length - 1}
            value={pos}
            onChange={(e) => setPos(Number(e.target.value))}
            className="replay__progreso"
          />
        </div>
      </div>
      <div className="alumno__contenido">
        <div className="alumno__subtitulos">
          <div className="subtitulos">
            {estables.slice(0, pos + 1).map((e, i) => (
              <div key={i} className={`subtitulo ${i === pos ? 'subtitulo--final' : 'subtitulo--final'}`}>
                {e.texto}
              </div>
            ))}
          </div>
        </div>
        <SenaPlayer senas={senasActuales} />
      </div>
    </div>
  )
}
