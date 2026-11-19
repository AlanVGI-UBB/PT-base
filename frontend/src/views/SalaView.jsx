import { useCallback, useEffect, useRef, useState } from 'react'
import { fetchSalaEstado, expulsarSesion, getToken } from '../api/cliente'
import { iniciar as iniciarCapturaPcm } from '../audio/capturaPcm'
import FinalizarModal from '../components/FinalizarModal'
import Feedback from '../components/Feedback'
import EstadoConexion from '../components/EstadoConexion'
import SenaPlayer from '../components/SenaPlayer'
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
  const surface = terminos.map((t) => t.texto_visible).filter(Boolean)
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

export default function SalaView({ roomId, user, onVolver }) {
  const [rol, setRol] = useState(null)
  const [determinando, setDeterminando] = useState(true)
  const [subtitulos, setSubtitulos] = useState([])
  const [sena, setSena] = useState(null)
  const [grabando, setGrabando] = useState(false)
  const [pausado, setPausado] = useState(false)
  const [finalizando, setFinalizando] = useState(false)
  const [nivelAudio, setNivelAudio] = useState(0)
  const [sinAudio, setSinAudio] = useState(false)
  const [sesionIniciada, setSesionIniciada] = useState(false)
  const [modalAbierto, setModalAbierto] = useState(false)
  const [feedback, setFeedback] = useState(null)
  const [tiempo, setTiempo] = useState(0)
  const [tamFuente, setTamFuente] = useState(() => Number(localStorage.getItem(FUENTE_KEY)) || 18)

  const capturaRef = useRef(null)
  const ultimoAudioRef = useRef(0)
  const subtitulosRef = useRef(null)
  const intervalRef = useRef(null)
  const senaTimeoutRef = useRef(null)
  const volverTimeoutRef = useRef(null)
  const finalizarFallbackRef = useRef(null)

  useEffect(() => {
    if (!roomId || !user) return
    fetchSalaEstado(roomId)
      .then((estado) => {
        const r = estado.activa ? 'listener' : 'emitter'
        setRol(r)
        setDeterminando(false)
        if (r === 'listener') setSesionIniciada(true)
      })
      .catch(() => {
        setDeterminando(false)
        setFeedback({ tipo: 'error', mensaje: 'No se pudo conectar con el servidor. Verifica tu conexión e inténtalo de nuevo.' })
      })
  }, [roomId, user])

  const token = getToken()
  const wsUrl = rol && sesionIniciada && token
    ? `${WS_URL}/ws/sala/${roomId}?rol=${rol}&token=${encodeURIComponent(token)}`
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
        setSena(data.senas)
        clearTimeout(senaTimeoutRef.current)
        senaTimeoutRef.current = setTimeout(() => setSena(null), 4000)
      }
    } else if (data.type === 'clase_finalizada') {
      clearTimeout(finalizarFallbackRef.current)
      setFinalizando(false)
      setSesionIniciada(false)
      setFeedback({ tipo: 'info', mensaje: 'La clase terminó y se guardó en tu historial' })
      volverTimeoutRef.current = setTimeout(() => { window.location.hash = '#/dashboard' }, 2500)
    } else if (data.type === 'emisor_desconectado') {
      setFeedback({ tipo: 'warning', mensaje: data.mensaje || 'El emisor se desconectó. La clase se guardará automáticamente.' })
    } else if (data.type === 'error') {
      const mensaje = data.mensaje || 'Ocurrió un error en la conexión'
      setFeedback({ tipo: 'error', mensaje })
      if (/token/i.test(mensaje)) expulsarSesion()
    }
  }, [])

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
      clearTimeout(senaTimeoutRef.current)
      clearTimeout(volverTimeoutRef.current)
      clearTimeout(finalizarFallbackRef.current)
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
      setTiempo(0)
      intervalRef.current = setInterval(() => setTiempo((t) => t + 1), 1000)
      setSesionIniciada(true)
    } catch {
      setFeedback({
        tipo: 'error',
        mensaje: 'Permiso de micrófono denegado o dispositivo no disponible. Actívalo en el navegador e inténtalo de nuevo.',
      })
    }
  }, [wsRef])

  const pausar = useCallback(() => {
    capturaRef.current?.pausar()
    setPausado(true)
    setNivelAudio(0)
    setSinAudio(false)
  }, [])

  const reanudar = useCallback(() => {
    ultimoAudioRef.current = Date.now()
    setSinAudio(false)
    capturaRef.current?.reanudar()
    setPausado(false)
  }, [])

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

  if (determinando) {
    return (
      <main className="sala">
        <p style={{ padding: '2rem', textAlign: 'center', color: 'var(--muted)' }}>
          Verificando sala...
        </p>
      </main>
    )
  }

  if (!rol) {
    return (
      <main className="sala">
        <div style={{ padding: '2rem', display: 'flex', flexDirection: 'column', gap: '1rem', alignItems: 'center' }}>
          <Feedback tipo="error" mensaje={feedback?.mensaje} onClose={() => setFeedback(null)} />
          <button className="btn btn--ghost" onClick={onVolver}>
            <IconoSalir size={18} /> <span>Volver al inicio</span>
          </button>
        </div>
      </main>
    )
  }

  return (
    <main className="sala">
      <header className="sala-topbar">
        {rol === 'emitter' && grabando ? (
          <button
            className="btn btn--ghost"
            onClick={abrirModalFinalizar}
            title="Para salir debes finalizar y guardar la sesión"
          >
            <IconoSalir size={18} /> <span>Salir</span>
          </button>
        ) : (
          <button className="btn btn--ghost" onClick={onVolver}>
            <IconoSalir size={18} /> <span>Salir</span>
          </button>
        )}
        <h1 className="sala-titulo">{roomId.replace('-', ' — ')}</h1>
        {estadoWs === 'conectado' && (
          <span className="sala-en-vivo">
            <span className="sala-en-vivo__dot" />
            EN VIVO
          </span>
        )}
        {sesionIniciada && <EstadoConexion estado={estadoWs} intentos={intentos} />}
        {estadoWs === 'fallo' && (
          <button className="btn btn--ghost" onClick={reintentar}>
            Reintentar conexión
          </button>
        )}
      </header>

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
                <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
                <line x1="9" y1="9" x2="15" y2="9"/>
                <line x1="9" y1="13" x2="15" y2="13"/>
                <line x1="9" y1="17" x2="13" y2="17"/>
              </svg>
              <span>Transcripción en Tiempo Real</span>
            </div>
            <div className="sala-subtitulos__tamano">
              <button onClick={() => cambiarTam(2)} aria-label="Aumentar tamaño de letra">A+</button>
              <button onClick={() => cambiarTam(-2)} aria-label="Disminuir tamaño de letra">A−</button>
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
            {grabando && !pausado && (
              <>
                <IconoMicrofono size={14} />
                <span>Escuchando al profesor...</span>
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
              </>
            )}
            {grabando && pausado && <span style={{ color: 'var(--warning)' }}>Pausado</span>}
            {finalizando && <span style={{ color: 'var(--muted)' }}>Finalizando y guardando...</span>}
            {!grabando && !finalizando && (
              <span style={{ color: 'var(--muted)' }}>
                {rol === 'listener' ? 'Conectado como oyente' : 'Listo para iniciar'}
              </span>
            )}
          </div>
        </section>

        <section className="sala-video">
          <div className="sala-video__player">
            {sena ? (
              <SenaPlayer senas={sena} />
            ) : (
              <div className="sala-video__placeholder">
                <div className="sala-video__placeholder-icon">
                  <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ margin: '0 auto' }}>
                    <path d="M23 7l-7 5 7 5V7z"/>
                    <rect x="1" y="5" width="15" height="14" rx="2" ry="2"/>
                  </svg>
                </div>
                <div className="sala-video__placeholder-text">
                  Esperando video de la seña...
                </div>
              </div>
            )}
          </div>
        </section>
      </div>

      {rol === 'emitter' && (
        <footer className="sala-bottombar">
          <div className="sala-estado">
            <div className="sala-estado__label">Estado del Sistema</div>
            <div className="sala-estado__sub">
              {grabando && (
                <>
                  <span>Transmitiendo · {formatearTiempo(tiempo)}</span>
                  {!pausado && (
                    <span className="nivel-audio" aria-hidden="true">
                      <span className="nivel-audio__barra" style={{ width: `${nivelPorcentaje}%` }} />
                    </span>
                  )}
                </>
              )}
              {finalizando && <span>Finalizando y guardando...</span>}
              {!grabando && !finalizando && <span>Listo para iniciar</span>}
            </div>
          </div>
          <div className="sala-controles">
            {!grabando ? (
              <button className="btn btn--ghost-pause" onClick={iniciar} disabled={finalizando}>
                <IconoMicrofono size={18} /> {finalizando ? 'Guardando...' : 'Iniciar Transmisión'}
              </button>
            ) : (
              <>
                <button className="btn btn--ghost-pause" onClick={pausado ? reanudar : pausar}>
                  <IconoPausa size={18} />
                  {pausado ? 'Reanudar' : 'Pausar'} Transcripción
                </button>
                <button className="btn btn--detener-finalizar" onClick={abrirModalFinalizar}>
                  <IconoStop size={16} />
                  Finalizar y Guardar
                </button>
              </>
            )}
          </div>
        </footer>
      )}

      <FinalizarModal
        open={modalAbierto}
        onConfirm={confirmarFinalizar}
        onCancel={cancelarFinalizar}
      />
    </main>
  )
}
