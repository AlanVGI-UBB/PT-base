import { useEffect, useMemo, useRef, useState } from 'react'
import { fetchHistorialDetalle } from '../api/cliente'
import { liberarClips } from '../api/clips'
import Feedback from '../components/Feedback'
import SenaPlayer from '../components/SenaPlayer'
import ThemeToggle from '../components/ThemeToggle'

const ETIQUETA_DISCONTINUIDAD = {
  pausa: 'Transmisión pausada',
  reanudacion: 'Transmisión reanudada',
  desconexion: 'Emisor desconectado',
}

const FUENTE_KEY = 'puente_lsch_font_size'
const LECTURA_BASE_MS = 1400
const LECTURA_POR_PALABRA_MS = 260
const LECTURA_MIN_MS = 2000
const LECTURA_MAX_MS = 5500
const TRANSICION_MS = 350

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
  const surface = Array.from(
    new Set(senas.map((t) => t.texto_detectado || t.texto_visible).filter(Boolean))
  ).sort((a, b) => b.length - a.length)
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

function calcularTiempoLecturaBaseMs(texto) {
  const palabras = (texto || '').trim().split(/\s+/).filter(Boolean).length
  return Math.min(LECTURA_MAX_MS, Math.max(LECTURA_MIN_MS, LECTURA_BASE_MS + palabras * LECTURA_POR_PALABRA_MS))
}

function formatearMarcaTiempo(ms) {
  const totalSeg = Math.max(0, Math.floor((ms || 0) / 1000))
  const min = String(Math.floor(totalSeg / 60)).padStart(2, '0')
  const seg = String(totalSeg % 60).padStart(2, '0')
  return `${min}:${seg}`
}

export default function ClaseDetailView({ theme, onToggleTheme }) {
  const [clase, setClase] = useState(null)
  const [eventos, setEventos] = useState([])
  const [error, setError] = useState('')
  const [modo, setModo] = useState('apunte')
  const [tamFuente, setTamFuente] = useState(() => Number(localStorage.getItem(FUENTE_KEY)) || 18)
  const [replayPos, setReplayPos] = useState(0)
  const [senaIdx, setSenaIdx] = useState(0)
  const [replayRunId, setReplayRunId] = useState(0)
  const [replayPlaying, setReplayPlaying] = useState(false)
  const [replayFinalizado, setReplayFinalizado] = useState(false)
  const [replayVelocidad, setReplayVelocidad] = useState(1)
  const [clipsHechosPara, setClipsHechosPara] = useState(null)
  const [lecturaHechaPara, setLecturaHechaPara] = useState(null)

  const claseId = window.location.hash.split('/').pop()
  const subtitulosRef = useRef(null)
  const lecturaRef = useRef({ clave: null, restanteBase: 0 })

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

  useEffect(() => () => liberarClips(), [])

  const eventosApunte = useMemo(
    () => (eventos || []).filter((e) => {
      const tipo = e.tipo || 'segmento'
      if (tipo !== 'segmento') return true
      return Boolean(e.estable || e.texto)
    }),
    [eventos],
  )
  const estables = useMemo(
    () => (eventos || []).filter((e) => (e.tipo || 'segmento') === 'segmento' && (e.estable || e.texto)),
    [eventos],
  )
  const eventoActual = modo === 'replay' ? (estables[replayPos] || null) : null
  const tituloPantalla = clase ? (clase.titulo || `${clase.cod_ramo} — ${clase.seccion}`) : ''
  const senasActuales = useMemo(
    () => (eventoActual ? parseSenas(eventoActual.senas) : []),
    [eventoActual],
  )
  const senaActual = senasActuales[senaIdx] || null
  const claveSegmento = `${replayRunId}-${replayPos}`

  const clipsTerminados = senasActuales.length === 0 || clipsHechosPara === claveSegmento
  const lecturaCompleta = lecturaHechaPara === claveSegmento

  // Temporizador de lectura proporcional al texto (pausa y ajusta velocidad sin reiniciar)
  useEffect(() => {
    if (modo !== 'replay' || !replayPlaying || !eventoActual || lecturaCompleta) {
      return undefined
    }
    if (lecturaRef.current.clave !== claveSegmento) {
      lecturaRef.current = {
        clave: claveSegmento,
        restanteBase: calcularTiempoLecturaBaseMs(eventoActual.texto),
      }
    }
    const esperaMs = Math.max(0, Math.round(lecturaRef.current.restanteBase / replayVelocidad))
    const inicio = Date.now()
    const timer = setTimeout(() => {
      lecturaRef.current.restanteBase = 0
      setLecturaHechaPara(claveSegmento)
    }, esperaMs)

    return () => {
      clearTimeout(timer)
      const transcurridoBase = (Date.now() - inicio) * replayVelocidad
      lecturaRef.current.restanteBase = Math.max(0, lecturaRef.current.restanteBase - transcurridoBase)
    }
  }, [modo, replayPlaying, eventoActual, claveSegmento, lecturaCompleta, replayVelocidad])

  // Avanza al siguiente segmento cuando terminan tanto sus clips como el tiempo mínimo de lectura
  useEffect(() => {
    if (modo !== 'replay' || !replayPlaying || estables.length === 0) return undefined
    if (!clipsTerminados || !lecturaCompleta) return undefined

    const esperaTransicion = Math.round(TRANSICION_MS / replayVelocidad)
    const timer = setTimeout(() => {
      if (replayPos < estables.length - 1) {
        setReplayPos((p) => p + 1)
        setSenaIdx(0)
      } else {
        setReplayPlaying(false)
        setReplayFinalizado(true)
      }
    }, esperaTransicion)

    return () => clearTimeout(timer)
  }, [modo, replayPlaying, clipsTerminados, lecturaCompleta, replayPos, estables.length, replayVelocidad])

  useEffect(() => {
    if (subtitulosRef.current) {
      subtitulosRef.current.scrollTop = subtitulosRef.current.scrollHeight
    }
  }, [replayPos, modo])

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

  const entrarAReplay = () => {
    setModo('replay')
    setReplayPos(0)
    setSenaIdx(0)
    setReplayPlaying(false)
    setReplayFinalizado(false)
    setClipsHechosPara(null)
    setLecturaHechaPara(null)
    setReplayRunId((r) => r + 1)
  }

  const saltarAPosicion = (nuevaPos) => {
    setReplayPos(nuevaPos)
    setSenaIdx(0)
    setReplayFinalizado(false)
    setClipsHechosPara(null)
    setLecturaHechaPara(null)
    setReplayRunId((r) => r + 1)
  }

  const handleTogglePlay = () => {
    if (estables.length === 0) return
    if (replayPlaying) {
      setReplayPlaying(false)
    } else {
      if (replayFinalizado || (replayPos >= estables.length - 1 && clipsTerminados && lecturaCompleta)) {
        saltarAPosicion(0)
      }
      setReplayPlaying(true)
    }
  }

  const handleChangePos = (e) => {
    saltarAPosicion(Number(e.target.value))
  }

  const estadoTexto = replayPlaying
    ? 'Reproduciendo'
    : (replayFinalizado ? 'Finalizado' : 'En pausa')
  const marcaTiempoActual = eventoActual ? formatearMarcaTiempo(eventoActual.timestamp_ms) : '00:00'

  return (
    <main className="sala">
      <header className="sala-topbar">
        <div className="sala-topbar__left">
          <button type="button" className="btn btn--ghost" onClick={() => { window.location.hash = '#/historial' }}>
            <IconoVolver size={16} /> <span>Volver</span>
          </button>
          <span className="sala-topbar__sep" aria-hidden="true" />
          <span className="sala-topbar__brand">Puente LSCh</span>
        </div>

        <div className="sala-topbar__center">
          {clase.cod_ramo && <span className="code-pill">{clase.cod_ramo}</span>}
          <h1 className="sala-titulo">{tituloPantalla}</h1>
        </div>

        <div className="sala-topbar__right">
          {clase.cierre === 'timeout' && (
            <span className="badge-incompleto">Registro incompleto</span>
          )}
          <span className="sala-badge-historial">HISTORIAL</span>
          {onToggleTheme && <ThemeToggle theme={theme} onToggle={onToggleTheme} />}
        </div>
      </header>

      <div className="sala-grid">
        <section className="sala-subtitulos">
          <div className="sala-subtitulos__header">
            <div className="sala-subtitulos__titulo">
              <IconoTranscripcion size={16} />
              <span>Transcripción</span>
            </div>
            <div className="sala-subtitulos__controls">
              <div className="sala-subtitulos__modos">
                <button
                  type="button"
                  className={`sala-subtitulos__modo-btn ${modo === 'apunte' ? 'sala-subtitulos__modo-btn--active' : ''}`}
                  onClick={() => { setModo('apunte'); setReplayPlaying(false) }}
                >
                  Apunte
                </button>
                <button
                  type="button"
                  className={`sala-subtitulos__modo-btn ${modo === 'replay' ? 'sala-subtitulos__modo-btn--active' : ''}`}
                  onClick={entrarAReplay}
                >
                  Replay
                </button>
              </div>
              <div className="sala-subtitulos__tamano">
                <button type="button" onClick={() => cambiarTam(-2)} aria-label="Disminuir tamaño de letra">A−</button>
                <button type="button" onClick={() => cambiarTam(2)} aria-label="Aumentar tamaño de letra">A+</button>
              </div>
            </div>
          </div>

          <div className="sala-subtitulos__contenido" ref={subtitulosRef} style={{ fontSize: `${tamFuente}px` }}>
            {modo === 'apunte' ? (
              eventosApunte.length === 0 ? (
                <p className="sala-subtitulos__vacio">No hay transcripción disponible.</p>
              ) : (
                eventosApunte.map((e, i) => {
                  const tipo = e.tipo || 'segmento'
                  if (tipo !== 'segmento') {
                    const etiqueta = ETIQUETA_DISCONTINUIDAD[tipo] || tipo
                    return (
                      <div
                        key={i}
                        className={`apunte-separador ${tipo === 'desconexion' ? 'apunte-separador--desconexion' : ''}`}
                        role="separator"
                      >
                        <span>{etiqueta} · {formatearMarcaTiempo(e.timestamp_ms)}</span>
                      </div>
                    )
                  }
                  return (
                    <p key={i} className="sala-subtitulo sala-subtitulo--final">
                      {highlight(e.texto, e.senas)}
                    </p>
                  )
                })
              )
            ) : estables.length === 0 ? (
              <p className="sala-subtitulos__vacio">No hay transcripción disponible.</p>
            ) : (
              estables.slice(0, replayPos + 1).map((e, i) => (
                <p
                  key={i}
                  className="sala-subtitulo sala-subtitulo--final"
                  style={i === replayPos ? { fontWeight: 500 } : { opacity: 0.55, cursor: 'pointer' }}
                  onClick={() => { if (i !== replayPos) saltarAPosicion(i) }}
                >
                  {highlight(e.texto, e.senas)}
                </p>
              ))
            )}
          </div>

          {modo === 'replay' && estables.length > 0 && (
            <div className="sala-subtitulos__status">
              <span>
                {estadoTexto}: {replayPos + 1} / {estables.length} · {marcaTiempoActual} · {replayVelocidad}x
                {senasActuales.length > 1 ? ` · seña ${Math.min(senaIdx + 1, senasActuales.length)}/${senasActuales.length}` : ''}
              </span>
            </div>
          )}
        </section>

        <section className="sala-video">
          <div className="sala-panel-header">
            <div className="sala-subtitulos__titulo">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M18 11V6a2 2 0 0 0-4 0v4"/>
                <path d="M14 10V4a2 2 0 0 0-4 0v6"/>
                <path d="M10 10.5V6a2 2 0 0 0-4 0v8"/>
                <path d="M18 8a2 2 0 1 1 4 0v6a8 8 0 0 1-8 8h-2c-2.8 0-4.5-.86-5.99-2.34l-3.6-3.6a2 2 0 0 1 2.83-2.82L7 15"/>
              </svg>
              <span>Apoyo terminológico LSCh</span>
            </div>
          </div>

          <div className="sala-video__body">
            <div className="sala-video__player">
              {modo === 'replay' && senaActual ? (
                <SenaPlayer
                  sena={senaActual}
                  playId={`${replayRunId}-${replayPos}-${senaIdx}`}
                  reproduciendo={replayPlaying && !clipsTerminados}
                  velocidad={replayVelocidad}
                  onEnded={() => {
                    if (!replayPlaying) return
                    if (senaIdx + 1 < senasActuales.length) {
                      setSenaIdx((i) => i + 1)
                    } else {
                      setClipsHechosPara(claveSegmento)
                    }
                  }}
                />
              ) : (
                <div className="sala-video__placeholder">
                  <div className="sala-video__placeholder-icon">
                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M23 7l-7 5 7 5V7z"/>
                      <rect x="1" y="5" width="15" height="14" rx="2" ry="2"/>
                    </svg>
                  </div>
                  <div className="sala-video__placeholder-text">
                    {modo === 'replay'
                      ? 'Sin señas en este segmento'
                      : <>Video de la seña disponible<br/>al iniciar el replay</>}
                  </div>
                </div>
              )}
            </div>
          </div>
        </section>
      </div>

      {modo === 'replay' && (
        <footer className="sala-bottombar">
          <div className="sala-estado">
            <span className="sala-estado__label">Modo Replay</span>
            <span className="sala-estado__sub">Ritmo continuo de lectura y señas</span>
          </div>
          <div className="sala-controles">
            <button type="button" className="btn btn--primary" onClick={handleTogglePlay}>
              {replayPlaying ? <IconoPausa size={15} /> : <IconoPlay size={15} />}
              <span>{replayPlaying ? 'Pausar' : 'Reproducir'}</span>
            </button>
            <div className="sala-velocidades" role="group" aria-label="Velocidad de reproducción">
              {[1, 1.5, 2].map((v) => (
                <button
                  key={v}
                  type="button"
                  className={`sala-velocidad-btn ${replayVelocidad === v ? 'sala-velocidad-btn--active' : ''}`}
                  onClick={() => setReplayVelocidad(v)}
                >
                  {v}x
                </button>
              ))}
            </div>
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
