import { useEffect, useRef, useState } from 'react'
import { fetchHistorialDetalle } from '../api/cliente'
import Feedback from '../components/Feedback'
import SenaPlayer from '../components/SenaPlayer'

const FUENTE_KEY = 'puente_lsch_font_size'

const IconoVolver = ({ size = 18 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="19" y1="12" x2="5" y2="12"/>
    <polyline points="12 19 5 12 12 5"/>
  </svg>
)

const IconoTranscripcion = ({ size = 16 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
    <line x1="9" y1="9" x2="15" y2="9"/>
    <line x1="9" y1="13" x2="15" y2="13"/>
    <line x1="9" y1="17" x2="13" y2="17"/>
  </svg>
)

const IconoPlay = ({ size = 18 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor">
    <polygon points="5 3 19 12 5 21 5 3"/>
  </svg>
)

const IconoPausa = ({ size = 18 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor">
    <rect x="6" y="4" width="4" height="16" rx="1"/>
    <rect x="14" y="4" width="4" height="16" rx="1"/>
  </svg>
)

function highlight(texto, senasJson) {
  if (!texto || !senasJson) return texto
  let senas = []
  try { senas = JSON.parse(senasJson) } catch { return texto }
  const surface = senas.map((t) => t.texto_visible).filter(Boolean)
  if (surface.length === 0) return texto
  const pattern = new RegExp(
    `(${surface.map((s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')})`,
    'gi'
  )
  const parts = texto.split(pattern)
  return parts.map((part, i) => {
    if (i % 2 === 1) {
      return <strong key={i} className="termino">{part}</strong>
    }
    return part
  })
}

function parseSenas(senasRaw) {
  if (!senasRaw) return []
  try { return JSON.parse(senasRaw) } catch { return [] }
}

export default function ClaseDetailView() {
  const [clase, setClase] = useState(null)
  const [eventos, setEventos] = useState([])
  const [error, setError] = useState('')
  const [modo, setModo] = useState('apunte')
  const [tamFuente, setTamFuente] = useState(() => Number(localStorage.getItem(FUENTE_KEY)) || 18)
  const [replayPos, setReplayPos] = useState(0)
  const [replayPlaying, setReplayPlaying] = useState(false)
  const [replayVelocidad, setReplayVelocidad] = useState(1)
  const claseId = window.location.hash.split('/').pop()
  const subtitulosRef = useRef(null)
  const timeoutRef = useRef(null)

  useEffect(() => {
    setError('')
    fetchHistorialDetalle(claseId)
      .then((data) => {
        setClase(data.clase)
        setEventos(data.eventos || [])
      })
      .catch((e) => {
        setClase(null)
        setError(e.message || 'No se pudo cargar la clase')
      })
  }, [claseId])

  const estables = (eventos || []).filter((e) => e.estable || e.texto)
  const tituloPantalla = clase ? (clase.titulo || `${clase.cod_ramo} — ${clase.seccion}`) : ''
  const senasActuales = modo === 'replay' && estables[replayPos]
    ? parseSenas(estables[replayPos].senas)
    : []

  useEffect(() => {
    clearTimeout(timeoutRef.current)
    if (!replayPlaying || estables.length === 0 || replayPos >= estables.length - 1) {
      if (replayPos >= estables.length - 1 && replayPlaying) {
        setReplayPlaying(false)
      }
      return
    }
    const current = estables[replayPos]
    const next = estables[replayPos + 1]
    if (!current || !next) {
      setReplayPlaying(false)
      return
    }
    const delay = Math.max(200, ((next.timestamp_ms || 0) - (current.timestamp_ms || 0)) / replayVelocidad)
    const id = setTimeout(() => {
      setReplayPos((p) => p + 1)
    }, delay)
    timeoutRef.current = id
    return () => clearTimeout(id)
  }, [replayPlaying, replayPos, replayVelocidad, estables])

  useEffect(() => {
    if (subtitulosRef.current) {
      subtitulosRef.current.scrollTop = subtitulosRef.current.scrollHeight
    }
  }, [replayPos, modo])

  useEffect(() => {
    return () => clearTimeout(timeoutRef.current)
  }, [])

  const cambiarTam = (delta) => setTamFuente((s) => {
    const nuevo = Math.min(32, Math.max(12, s + delta))
    localStorage.setItem(FUENTE_KEY, String(nuevo))
    return nuevo
  })

  if (error) {
    return (
      <main className="vista">
        <div style={{ padding: '2rem', display: 'flex', flexDirection: 'column', gap: '1rem', alignItems: 'center' }}>
          <Feedback tipo="error" mensaje={error} />
          <button className="btn btn--ghost" onClick={() => window.location.hash = '#/historial'}>
            <IconoVolver size={18} /> <span>Volver al historial</span>
          </button>
        </div>
      </main>
    )
  }

  if (!clase) {
    return (
      <main className="vista">
        <p style={{ padding: '2rem', textAlign: 'center' }}>Cargando...</p>
      </main>
    )
  }

  const handleTogglePlay = () => {
    if (replayPlaying) {
      setReplayPlaying(false)
    } else {
      if (replayPos >= estables.length - 1) setReplayPos(0)
      setReplayPlaying(true)
    }
  }

  const handleChangePos = (e) => {
    setReplayPos(Number(e.target.value))
  }

  return (
    <main className="sala">
      <header className="sala-topbar">
        <button className="btn btn--ghost" onClick={() => window.location.hash = '#/historial'}>
          <IconoVolver size={18} /> <span>Volver</span>
        </button>
        <h1 className="sala-titulo">{tituloPantalla}</h1>
        <span className="sala-badge-historial">HISTORIAL</span>
      </header>

      <div className="sala-grid">
        <section className="sala-subtitulos">
          <div className="sala-subtitulos__header">
            <div className="sala-subtitulos__titulo">
              <IconoTranscripcion size={16} />
              <span>Transcripción</span>
            </div>
            <div className="sala-subtitulos__modos">
              <button
                className={`sala-subtitulos__modo-btn ${modo === 'apunte' ? 'sala-subtitulos__modo-btn--active' : ''}`}
                onClick={() => { setModo('apunte'); setReplayPlaying(false) }}
              >
                Apunte
              </button>
              <button
                className={`sala-subtitulos__modo-btn ${modo === 'replay' ? 'sala-subtitulos__modo-btn--active' : ''}`}
                onClick={() => { setModo('replay'); setReplayPos(0); setReplayPlaying(false) }}
              >
                Replay
              </button>
            </div>
            <div className="sala-subtitulos__tamano">
              <button onClick={() => cambiarTam(2)} aria-label="Aumentar tamaño de letra">A+</button>
              <button onClick={() => cambiarTam(-2)} aria-label="Disminuir tamaño de letra">A−</button>
            </div>
          </div>

          <div className="sala-subtitulos__contenido" ref={subtitulosRef} style={{ fontSize: `${tamFuente}px` }}>
            {estables.length === 0 ? (
              <p className="sala-subtitulos__vacio">No hay transcripción disponible.</p>
            ) : modo === 'apunte' ? (
              estables.map((e, i) => (
                <p key={i} className="sala-subtitulo sala-subtitulo--final">
                  {highlight(e.texto, e.senas)}
                </p>
              ))
            ) : (
              estables.slice(0, replayPos + 1).map((e, i) => (
                <p
                  key={i}
                  className="sala-subtitulo sala-subtitulo--final"
                  style={i === replayPos ? { fontWeight: 600 } : { opacity: 0.6 }}
                >
                  {highlight(e.texto, e.senas)}
                </p>
              ))
            )}
          </div>

          {modo === 'replay' && (
            <div className="sala-subtitulos__status">
              <span>Reproduciendo: {replayPos + 1} / {estables.length} · {replayVelocidad}x</span>
            </div>
          )}
        </section>

        <section className="sala-video">
          <div className="sala-video__player">
            {modo === 'replay' && senasActuales.length > 0 ? (
              <SenaPlayer senas={senasActuales} />
            ) : (
              <div className="sala-video__placeholder">
                <div className="sala-video__placeholder-icon">
                  <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ margin: '0 auto' }}>
                    <path d="M23 7l-7 5 7 5V7z"/>
                    <rect x="1" y="5" width="15" height="14" rx="2" ry="2"/>
                  </svg>
                </div>
                <div className="sala-video__placeholder-text">
                  Video de la seña disponible<br/>al iniciar el replay
                </div>
              </div>
            )}
          </div>
        </section>
      </div>

      {modo === 'replay' && (
        <footer className="sala-bottombar">
          <div className="sala-estado">
            <div className="sala-estado__label">Modo Replay</div>
            <div className="sala-estado__sub">Reproducción de la clase guardada</div>
          </div>
          <div className="sala-controles">
            <button className="btn btn--ghost-pause" onClick={handleTogglePlay}>
              {replayPlaying ? <IconoPausa size={18} /> : <IconoPlay size={18} />}
              {replayPlaying ? 'Pausar' : 'Reproducir'}
            </button>
            {[1, 1.5, 2].map((v) => (
              <button
                key={v}
                className={`btn ${replayVelocidad === v ? 'btn--detener-finalizar' : 'btn--ghost-pause'}`}
                onClick={() => setReplayVelocidad(v)}
                style={replayVelocidad === v ? { background: 'var(--accent)', color: '#fff' } : {}}
              >
                {v}x
              </button>
            ))}
            <input
              type="range"
              min={0}
              max={Math.max(0, estables.length - 1)}
              value={replayPos}
              onChange={handleChangePos}
              className="sala-bottombar__progreso"
              aria-label="Progreso del replay"
            />
          </div>
        </footer>
      )}
    </main>
  )
}
