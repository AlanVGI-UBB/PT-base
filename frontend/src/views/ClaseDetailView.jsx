import { useEffect, useRef, useState } from 'react'
import { fetchHistorialDetalle } from '../api/cliente'

const API_BASE = import.meta.env.VITE_API_URL
const API_URL = API_BASE !== undefined ? API_BASE : 'http://localhost:8000'

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

const IconoAjustes = ({ size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="3"/>
    <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
  </svg>
)

const IconoExpandir = ({ size = 16 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="15 3 21 3 21 9"/>
    <polyline points="9 21 3 21 3 15"/>
    <line x1="21" y1="3" x2="14" y2="10"/>
    <line x1="3" y1="21" x2="10" y2="14"/>
  </svg>
)

const IconoMas = ({ size = 18 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor">
    <circle cx="5" cy="12" r="2"/>
    <circle cx="12" cy="12" r="2"/>
    <circle cx="19" cy="12" r="2"/>
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

const IconoMano = ({ size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M18 11V6a2 2 0 0 0-4 0v5"/>
    <path d="M14 10V4a2 2 0 0 0-4 0v6"/>
    <path d="M10 10.5V6a2 2 0 0 0-4 0v8"/>
    <path d="M18 8a2 2 0 1 1 4 0v6a8 8 0 0 1-8 8h-2c-2.8 0-4.5-.86-5.99-2.34l-3.6-3.6a2 2 0 0 1 2.83-2.82L7 15"/>
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
  const [modo, setModo] = useState('apunte')
  const [tamFuente, setTamFuente] = useState(18)
  const [replayPos, setReplayPos] = useState(0)
  const [replayPlaying, setReplayPlaying] = useState(false)
  const [replayVelocidad, setReplayVelocidad] = useState(1)
  const claseId = window.location.hash.split('/').pop()
  const subtitulosRef = useRef(null)
  const timeoutRef = useRef(null)

  useEffect(() => {
    fetchHistorialDetalle(claseId)
      .then((data) => {
        setClase(data.clase)
        setEventos(data.eventos || [])
      })
      .catch(console.error)
  }, [claseId])

  const estables = (eventos || []).filter((e) => e.estable || e.texto)
  const tituloPantalla = clase ? (clase.titulo || `${clase.cod_ramo} — ${clase.seccion}`) : ''
  const senasActuales = modo === 'replay' && estables[replayPos]
    ? parseSenas(estables[replayPos].senas)
    : []
  const conceptoActual = senasActuales.length > 0 ? senasActuales[0] : null

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
        <div style={{ marginLeft: 'auto' }}>
          <button className="header__icon-btn" aria-label="Configuración">
            <IconoAjustes size={20} />
          </button>
        </div>
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
              <button onClick={() => setTamFuente((s) => Math.min(s + 2, 32))}>A+</button>
              <button onClick={() => setTamFuente((s) => Math.max(s - 2, 12))}>A−</button>
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
            {conceptoActual ? (
              <div className="concepto-card">
                <div className="concepto-card__label">CONCEPTO DE LA SEÑA</div>
                <div className="concepto-card__value">
                  <IconoMano size={20} />
                  <span>{conceptoActual.texto_visible}</span>
                </div>
              </div>
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
            <div className="sala-video__overlay">
              <button className="sala-video__icon-btn" title="Expandir">
                <IconoExpandir size={16} />
              </button>
              <button className="sala-video__icon-btn" title="Más opciones">
                <IconoMas size={18} />
              </button>
            </div>
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
            />
          </div>
        </footer>
      )}
    </main>
  )
}
