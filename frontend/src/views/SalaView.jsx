import { useCallback, useEffect, useRef, useState } from 'react'
import { fetchGlosario, fetchSalaEstado, expulsarSesion, getToken } from '../api/cliente'
import { liberarClips, precargar } from '../api/clips'
import { iniciar as iniciarCapturaPcm } from '../audio/capturaPcm'
import CondicionesModal from '../components/CondicionesModal'
import FinalizarModal from '../components/FinalizarModal'
import Feedback from '../components/Feedback'
import EstadoConexion from '../components/EstadoConexion'
import SenaPlayer from '../components/SenaPlayer'
import ThemeToggle from '../components/ThemeToggle'
import { useColaSenas } from '../hooks/useColaSenas'
import { useWebSocket } from '../hooks/useWebSocket'

const WS_BASE = import.meta.env.VITE_WS_URL
const WS_ORIGIN = typeof window !== 'undefined'
  ? `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}`
  : 'ws://localhost:8000'
const WS_URL = WS_BASE === undefined ? 'ws://localhost:8000' : (WS_BASE || WS_ORIGIN)
const FUENTE_KEY = 'puente_lsch_font_size'
const UMBRAL_SILENCIO = 0.004
const SILENCIO_AVISO_MS = 10000

const IconoMicrofono = ({ size = 18 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
    <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
    <line x1="12" y1="19" x2="12" y2="23"/>
    <line x1="8" y1="23" x2="16" y2="23"/>
  </svg>
)

const IconoSalir = ({ size = 18 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="19" y1="12" x2="5" y2="12"/>
    <polyline points="12 19 5 12 12 5"/>
  </svg>
)

const IconoPausa = ({ size = 18 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor">
    <rect x="6" y="4" width="4" height="16" rx="1"/>
    <rect x="14" y="4" width="4" height="16" rx="1"/>
  </svg>
)

const IconoStop = ({ size = 18 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor">
    <rect x="5" y="5" width="14" height="14" rx="2"/>
  </svg>
)

function highlightText(texto, terminos) {
  if (!texto || !terminos || terminos.length === 0) return texto
  const surface = Array.from(
    new Set(terminos.map((t) => t.texto_detectado || t.texto_visible).filter(Boolean))
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

function formatearTiempo(segundos) {
  const m = String(Math.floor(segundos / 60)).padStart(2, '0')
  const s = String(segundos % 60).padStart(2, '0')
  return `${m}:${s}`
}

function getInitials(nombre = '', apellido = '') {
  const n = (nombre || '').trim()
  const a = (apellido || '').trim()
  if (n && a) return `${n[0]}${a[0]}`.toUpperCase()
  if (n) return n.slice(0, 2).toUpperCase()
  return '?'
}

function parseRoomId(roomId = '') {
  const idx = roomId.lastIndexOf('-')
  if (idx === -1) return { codigo: roomId, seccion: '' }
  return { codigo: roomId.slice(0, idx), seccion: roomId.slice(idx + 1) }
}

export default function SalaView({ roomId, user, onVolver, theme, onToggleTheme }) {
  const [rol, setRol] = useState(null)
  const [determinando, setDeterminando] = useState(true)
  const [subtitulos, setSubtitulos] = useState([])
  const { actual: senaActual, pendientes: senasPendientes, omitidas: senasOmitidas, playId: senaPlayId, encolar, alTerminar } = useColaSenas()
  const [grabando, setGrabando] = useState(false)
  const [pausado, setPausado] = useState(false)
  const [sesionPausada, setSesionPausada] = useState(false)
  const [finalizando, setFinalizando] = useState(false)
  const [nivelAudio, setNivelAudio] = useState(0)
  const [sinAudio, setSinAudio] = useState(false)
  const [sesionIniciada, setSesionIniciada] = useState(false)
  const [condicionesConfirmadas, setCondicionesConfirmadas] = useState(false)
  const [modalCondicionesAbierto, setModalCondicionesAbierto] = useState(false)
  const [modalAbierto, setModalAbierto] = useState(false)
  const [feedback, setFeedback] = useState(null)
  const [mensajeSinTransmision, setMensajeSinTransmision] = useState('')
  const [tiempo, setTiempo] = useState(0)
  const [tamFuente, setTamFuente] = useState(() => Number(localStorage.getItem(FUENTE_KEY)) || 18)

  const capturaRef = useRef(null)
  const ultimoAudioRef = useRef(0)
  const subtitulosRef = useRef(null)
  const intervalRef = useRef(null)
  const volverTimeoutRef = useRef(null)
  const finalizarFallbackRef = useRef(null)

  useEffect(() => {
    if (!roomId || !user) return
    setDeterminando(true)
    setFeedback(null)
    setMensajeSinTransmision('')
    fetchSalaEstado(roomId)
      .then((estado) => {
        if (estado.curso_id) {
          fetchGlosario(estado.curso_id)
            .then((glosario) => precargar(glosario))
            .catch(() => {})
        }
        if (estado.activa) {
          setRol('listener')
          setSesionIniciada(true)
        } else if (estado.puede_capturar) {
          setRol('emitter')
        } else {
          setRol(null)
          setMensajeSinTransmision('Aún no hay una transmisión en esta sala')
        }
        setDeterminando(false)
      })
      .catch((err) => {
        setRol(null)
        setDeterminando(false)
        if (err?.status === 403) {
          setFeedback({ tipo: 'error', mensaje: err.message || 'No tienes acceso a esta sala' })
        } else {
          setFeedback({ tipo: 'error', mensaje: 'No se pudo conectar con el servidor. Verifica tu conexión e inténtalo de nuevo.' })
        }
      })
  }, [roomId, user])

  const [tokenSesion, setTokenSesion] = useState(() => getToken())

  useEffect(() => {
    setTokenSesion(getToken())
  }, [user?.rut])

  const wsUrl = rol && sesionIniciada && tokenSesion
    ? rol === 'emitter'
      ? (condicionesConfirmadas
          ? `${WS_URL}/ws/sala/${roomId}?rol=emitter&token=${encodeURIComponent(tokenSesion)}&condiciones=1`
          : null)
      : `${WS_URL}/ws/sala/${roomId}?rol=listener&token=${encodeURIComponent(tokenSesion)}`
    : null

  const manejarMensaje = useCallback((data) => {
    if (data.type === 'segmento') {
      setSubtitulos((prev) => {
        const entrada = {
          id: data.segment_id,
          texto: data.texto,
          final: Boolean(data.final),
          terminos: data.final ? (data.senas || []) : [],
        }
        const idx = prev.findIndex((s) => s.id === data.segment_id)
        if (idx !== -1) {
          const copia = [...prev]
          copia[idx] = entrada
          return copia
        }
        return [...prev, entrada]
      })
      if (data.final && data.senas && data.senas.length > 0) {
        encolar(data.senas)
      }
    } else if (data.type === 'estado_sesion') {
      setSesionPausada(data.estado === 'pausada')
    } else if (data.type === 'clase_finalizada') {
      clearTimeout(finalizarFallbackRef.current)
      setFinalizando(false)
      setSesionIniciada(false)
      setSesionPausada(false)
      setFeedback({ tipo: 'info', mensaje: 'La clase terminó y se guardó en tu historial' })
      volverTimeoutRef.current = setTimeout(() => { window.location.hash = '#/dashboard' }, 2500)
    } else if (data.type === 'emisor_desconectado') {
      setFeedback({ tipo: 'warning', mensaje: data.mensaje || 'El emisor se desconectó. La clase se guardará automáticamente.' })
    } else if (data.type === 'error') {
      const mensaje = data.mensaje || 'Ocurrió un error en la conexión'
      setSesionIniciada(false)
      setFeedback({ tipo: 'error', mensaje })
      if (/token/i.test(mensaje)) expulsarSesion()
    }
  }, [encolar])

  const { ws: wsRef, estado: estadoWs, intentos, enviar, reintentar } = useWebSocket(wsUrl, {
    onMessage: manejarMensaje,
  })

  useEffect(() => {
    if (subtitulosRef.current) {
      subtitulosRef.current.scrollTop = subtitulosRef.current.scrollHeight
    }
  }, [subtitulos])

  useEffect(() => {
    return () => {
      capturaRef.current?.detener()
      capturaRef.current = null
      clearInterval(intervalRef.current)
      clearTimeout(volverTimeoutRef.current)
      clearTimeout(finalizarFallbackRef.current)
      liberarClips()
    }
  }, [])

  const iniciar = useCallback(async () => {
    try {
      ultimoAudioRef.current = Date.now()
      setSinAudio(false)
      setNivelAudio(0)
      const captura = await iniciarCapturaPcm({
        onTrama: (buffer) => {
          if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(buffer)
          }
        },
        onNivel: (rms) => {
          setNivelAudio(rms)
          if (rms >= UMBRAL_SILENCIO) {
            ultimoAudioRef.current = Date.now()
            setSinAudio(false)
          } else if (Date.now() - ultimoAudioRef.current >= SILENCIO_AVISO_MS) {
            setSinAudio(true)
          }
        },
      })
      capturaRef.current = captura
      setGrabando(true)
      setPausado(false)
      setSesionPausada(false)
      setTiempo(0)
      intervalRef.current = setInterval(() => setTiempo((t) => t + 1), 1000)
      setCondicionesConfirmadas(true)
      setSesionIniciada(true)
    } catch {
      setFeedback({
        tipo: 'error',
        mensaje: 'Permiso de micrófono denegado o dispositivo no disponible. Actívalo en el navegador e inténtalo de nuevo.',
      })
    }
  }, [wsRef])

  const abrirModalCondiciones = useCallback(() => setModalCondicionesAbierto(true), [])
  const cancelarCondiciones = useCallback(() => setModalCondicionesAbierto(false), [])
  const confirmarCondiciones = useCallback(() => {
    setModalCondicionesAbierto(false)
    iniciar()
  }, [iniciar])

  const pausar = useCallback(() => {
    capturaRef.current?.pausar()
    setPausado(true)
    setSesionPausada(true)
    setNivelAudio(0)
    setSinAudio(false)
    enviar(JSON.stringify({ action: 'pausar' }))
  }, [enviar])

  const reanudar = useCallback(() => {
    ultimoAudioRef.current = Date.now()
    setSinAudio(false)
    capturaRef.current?.reanudar()
    setPausado(false)
    setSesionPausada(false)
    enviar(JSON.stringify({ action: 'reanudar' }))
  }, [enviar])

  const abrirModalFinalizar = useCallback(() => setModalAbierto(true), [])
  const cancelarFinalizar = useCallback(() => setModalAbierto(false), [])

  const confirmarFinalizar = useCallback((titulo) => {
    clearInterval(intervalRef.current)
    capturaRef.current?.detener()
    capturaRef.current = null
    setNivelAudio(0)
    setSinAudio(false)
    setGrabando(false)
    setPausado(false)
    setSesionPausada(false)
    setModalAbierto(false)
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      setFinalizando(true)
      enviar(JSON.stringify({ action: 'finalizar', titulo: titulo || null }))
      finalizarFallbackRef.current = setTimeout(() => {
        setFinalizando(false)
        setSesionIniciada(false)
        window.location.hash = '#/dashboard'
      }, 6000)
    } else {
      setSesionIniciada(false)
      setTimeout(() => { window.location.hash = '#/dashboard' }, 200)
    }
  }, [enviar, wsRef])

  const cambiarTam = (delta) => setTamFuente((s) => {
    const nuevo = Math.min(32, Math.max(12, s + delta))
    localStorage.setItem(FUENTE_KEY, String(nuevo))
    return nuevo
  })

  const nivelPorcentaje = Math.min(100, Math.round(Math.sqrt(nivelAudio) * 180))
  const { codigo: codigoRamo, seccion: seccionSala } = parseRoomId(roomId)

  if (determinando) {
    return (
      <main className="sala">
        <p className="dashboard__vacio">Verificando sala...</p>
      </main>
    )
  }

  if (!rol) {
    return (
      <main className="sala">
        <header className="sala-topbar">
          <div className="sala-topbar__left">
            <button type="button" className="btn btn--ghost" onClick={onVolver}>
              <IconoSalir size={16} /> <span>Salir</span>
            </button>
            <span className="sala-topbar__sep" aria-hidden="true" />
            <span className="sala-topbar__brand">Puente LSCh</span>
          </div>
          <div className="sala-topbar__right">
            {onToggleTheme && <ThemeToggle theme={theme} onToggle={onToggleTheme} />}
          </div>
        </header>
        <div style={{ padding: '3rem 1.5rem', display: 'flex', flexDirection: 'column', gap: '1rem', alignItems: 'center' }}>
          {mensajeSinTransmision ? (
            <Feedback tipo="info" mensaje={mensajeSinTransmision} />
          ) : (
            <Feedback tipo="error" mensaje={feedback?.mensaje} onClose={() => setFeedback(null)} />
          )}
          <button type="button" className="btn btn--outline" onClick={onVolver}>
            <IconoSalir size={16} /> <span>Volver al inicio</span>
          </button>
        </div>
      </main>
    )
  }

  return (
    <main className="sala">
      <header className="sala-topbar">
        <div className="sala-topbar__left">
          {rol === 'emitter' && grabando ? (
            <button
              type="button"
              className="btn btn--ghost"
              onClick={abrirModalFinalizar}
              title="Para salir debes finalizar y guardar la sesión"
            >
              <IconoSalir size={16} /> <span>Salir</span>
            </button>
          ) : (
            <button type="button" className="btn btn--ghost" onClick={onVolver}>
              <IconoSalir size={16} /> <span>Salir</span>
            </button>
          )}
          <span className="sala-topbar__sep" aria-hidden="true" />
          <span className="sala-topbar__brand">Puente LSCh</span>
        </div>

        <div className="sala-topbar__center">
          <span className="code-pill">{codigoRamo}</span>
          {seccionSala && <h1 className="sala-titulo">Sección {seccionSala}</h1>}
        </div>

        <div className="sala-topbar__right">
          {estadoWs === 'conectado' && (
            <span className={`sala-en-vivo ${sesionPausada ? 'sala-en-vivo--pausada' : ''}`}>
              <span className="sala-en-vivo__dot" />
              {sesionPausada ? 'EN PAUSA' : 'EN VIVO'}
            </span>
          )}
          {sesionIniciada && <EstadoConexion estado={estadoWs} intentos={intentos} />}
          {estadoWs === 'fallo' && (
            <button type="button" className="btn btn--outline btn--sm" onClick={reintentar}>
              Reintentar
            </button>
          )}
          {onToggleTheme && <ThemeToggle theme={theme} onToggle={onToggleTheme} />}
          {user && (
            <div className="header__avatar" title={`${user.nombre} ${user.apellido}`}>
              {getInitials(user.nombre, user.apellido)}
            </div>
          )}
        </div>
      </header>

      {sesionPausada && (
        <div className="sala-pausa-banner" role="status">
          Transmisión en pausa
        </div>
      )}

      {feedback && (
        <div style={{ flexShrink: 0 }}>
          <Feedback tipo={feedback.tipo} mensaje={feedback.mensaje} onClose={() => setFeedback(null)} />
        </div>
      )}

      {sinAudio && (
        <div style={{ flexShrink: 0 }}>
          <Feedback tipo="warning" mensaje="No se detecta audio en el micrófono" />
        </div>
      )}

      <div className="sala-grid">
        <section className="sala-subtitulos">
          <div className="sala-subtitulos__header">
            <div className="sala-subtitulos__titulo">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="3" y1="6" x2="21" y2="6"/>
                <line x1="3" y1="12" x2="17" y2="12"/>
                <line x1="3" y1="18" x2="14" y2="18"/>
              </svg>
              <span>Transcripción en tiempo real</span>
            </div>
            <div className="sala-subtitulos__tamano">
              <button type="button" onClick={() => cambiarTam(-2)} aria-label="Disminuir tamaño de letra">A−</button>
              <button type="button" onClick={() => cambiarTam(2)} aria-label="Aumentar tamaño de letra">A+</button>
            </div>
          </div>

          <div className="sala-subtitulos__contenido" ref={subtitulosRef} style={{ fontSize: `${tamFuente}px` }}>
            {subtitulos.length === 0 ? (
              <p className="sala-subtitulos__vacio">Esperando transcripción...</p>
            ) : (
              subtitulos.map((s) => (
                <p key={s.id} className={`sala-subtitulo ${s.final ? 'sala-subtitulo--final' : 'sala-subtitulo--provisional'}`}>
                  {s.final ? highlightText(s.texto, s.terminos) : s.texto}
                </p>
              ))
            )}
          </div>

          <div className="sala-subtitulos__status">
            <div className="sala-subtitulos__status-left">
              {grabando && !pausado && (
                <>
                  <IconoMicrofono size={14} />
                  <span>Escuchando al docente</span>
                </>
              )}
              {((grabando && pausado) || (rol === 'listener' && sesionPausada)) && (
                <span style={{ color: 'var(--warn-fg)', fontWeight: 600 }}>Transmisión en pausa</span>
              )}
              {finalizando && <span>Finalizando y guardando...</span>}
              {!grabando && !finalizando && !(rol === 'listener' && sesionPausada) && (
                <span>
                  {rol === 'listener' ? 'Conectado como oyente' : 'Listo para iniciar'}
                </span>
              )}
            </div>
            {grabando && !pausado && (
              <span
                className="nivel-audio"
                role="meter"
                aria-label="Nivel de entrada del micrófono"
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={nivelPorcentaje}
              >
                <span className="nivel-audio__barra" style={{ width: `${nivelPorcentaje}%` }} />
              </span>
            )}
          </div>
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
              {senaActual ? (
                <SenaPlayer sena={senaActual} playId={senaPlayId} onEnded={alTerminar} />
              ) : (
                <div className="sala-video__placeholder">
                  <div className="sala-video__placeholder-icon">
                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M23 7l-7 5 7 5V7z"/>
                      <rect x="1" y="5" width="15" height="14" rx="2" ry="2"/>
                    </svg>
                  </div>
                  <div className="sala-video__placeholder-text">
                    Esperando concepto del glosario...
                  </div>
                </div>
              )}
            </div>

            {(senasPendientes.length > 0 || senasOmitidas > 0) && (
              <div className="cola-senas" role="status">
                <span className="cola-senas__label">En cola ({senasPendientes.length})</span>
                {senasPendientes.length > 0 && (
                  <div className="cola-senas__chips">
                    {senasPendientes.map((item, idx) => (
                      <span key={`${item.termino_id || item.texto_visible}-${idx}`} className="cola-senas__chip">
                        {item.texto_visible}
                      </span>
                    ))}
                  </div>
                )}
                {senasOmitidas > 0 && (
                  <span className="cola-senas__omitidas">
                    {senasOmitidas} {senasOmitidas === 1 ? 'omitida' : 'omitidas'} · disponibles en el historial
                  </span>
                )}
              </div>
            )}
          </div>
        </section>
      </div>

      {rol === 'emitter' && (
        <footer className="sala-bottombar">
          <div className="sala-estado">
            <span className="sala-estado__label">
              {grabando
                ? (pausado ? `En pausa · ${formatearTiempo(tiempo)}` : `Sesión en vivo · ${formatearTiempo(tiempo)}`)
                : (finalizando ? 'Finalizando y guardando...' : 'Listo para iniciar')}
            </span>
            {grabando && !pausado && (
              <span className="nivel-audio" aria-hidden="true">
                <span className="nivel-audio__barra" style={{ width: `${nivelPorcentaje}%` }} />
              </span>
            )}
          </div>
          <div className="sala-controles">
            {!grabando ? (
              <button type="button" className="btn btn--primary" onClick={abrirModalCondiciones} disabled={finalizando}>
                <IconoMicrofono size={16} />
                <span>{finalizando ? 'Guardando...' : 'Iniciar transmisión'}</span>
              </button>
            ) : (
              <>
                <button type="button" className="btn btn--outline" onClick={pausado ? reanudar : pausar}>
                  <IconoPausa size={15} />
                  <span>{pausado ? 'Reanudar transcripción' : 'Pausar transcripción'}</span>
                </button>
                <button type="button" className="btn btn--danger" onClick={abrirModalFinalizar}>
                  <IconoStop size={14} />
                  <span>Finalizar y guardar</span>
                </button>
              </>
            )}
          </div>
        </footer>
      )}

      <CondicionesModal
        open={modalCondicionesAbierto}
        onConfirm={confirmarCondiciones}
        onCancel={cancelarCondiciones}
      />

      <FinalizarModal
        open={modalAbierto}
        onConfirm={confirmarFinalizar}
        onCancel={cancelarFinalizar}
      />
    </main>
  )
}
