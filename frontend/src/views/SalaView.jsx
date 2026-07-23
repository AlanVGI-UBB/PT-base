import { useCallback, useEffect, useRef, useState } from 'react'
import { fetchSalaEstado } from '../api/cliente'
import FinalizarModal from '../components/FinalizarModal'

const WS_URL = import.meta.env.VITE_WS_URL ?? 'ws://localhost:8000'

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

const IconoAjustes = ({ size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="3"/>
    <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
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

const IconoCheck = ({ size = 14 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="20 6 9 17 4 12"/>
  </svg>
)

const IconoMano = ({ size = 24 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M18 11V6a2 2 0 0 0-4 0v5"/>
    <path d="M14 10V4a2 2 0 0 0-4 0v6"/>
    <path d="M10 10.5V6a2 2 0 0 0-4 0v8"/>
    <path d="M18 8a2 2 0 1 1 4 0v6a8 8 0 0 1-8 8h-2c-2.8 0-4.5-.86-5.99-2.34l-3.6-3.6a2 2 0 0 1 2.83-2.82L7 15"/>
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

export default function SalaView({ roomId, user, onVolver }) {
  const [rol, setRol] = useState(null)
  const [estadoWs, setEstadoWs] = useState('desconectado')
  const [subtitulos, setSubtitulos] = useState([])
  const [conceptoClave, setConceptoClave] = useState(null)
  const [grabando, setGrabando] = useState(false)
  const [pausado, setPausado] = useState(false)
  const [tamFuente, setTamFuente] = useState(18)
  const [claseFinalizada, setClaseFinalizada] = useState(false)
  const [claseId, setClaseId] = useState(null)
  const [determinando, setDeterminando] = useState(true)
  const [modalAbierto, setModalAbierto] = useState(false)
  const wsRef = useRef(null)
  const recorderRef = useRef(null)
  const streamRef = useRef(null)
  const subtitulosRef = useRef(null)
  const [tiempo, setTiempo] = useState(0)
  const intervalRef = useRef(null)

  useEffect(() => {
    if (!roomId || !user) return
    fetchSalaEstado(roomId).then((estado) => {
      setRol(estado.activa ? 'listener' : 'emitter')
      setDeterminando(false)
    })
  }, [roomId, user])

  useEffect(() => {
    if (!rol || !roomId || !user) return
    const token = JSON.parse(localStorage.getItem('puente_lsch_auth')).token
    const url = `${WS_URL}/ws/sala/${roomId}?rol=${rol}&token=${token}`
    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => setEstadoWs('conectado')
    ws.onclose = () => setEstadoWs('desconectado')
    ws.onerror = () => setEstadoWs('desconectado')
    ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data)
        if (data.type === 'segmento') {
          if (data.final) {
            setSubtitulos((prev) => [
              ...prev,
              { id: data.segment_id, texto: data.texto, final: true, terminos: data.senas || [] },
            ])
            if (data.senas && data.senas.length > 0) {
              const principal = data.senas[0]
              setConceptoClave(principal)
              setTimeout(() => setConceptoClave(null), 4000)
            }
          } else {
            setSubtitulos((prev) => {
              const copia = [...prev]
              const last = copia[copia.length - 1]
              if (last && !last.final) {
                copia[copia.length - 1] = { ...last, texto: data.texto }
              } else {
                copia.push({ id: data.segment_id, texto: data.texto, final: false, terminos: [] })
              }
              return copia
            })
          }
        } else if (data.type === 'clase_finalizada') {
          setClaseFinalizada(true)
          setClaseId(data.clase_id)
        } else if (data.type === 'error') {
          window.location.hash = '#/dashboard'
        }
      } catch {}
    }

    return () => ws.close()
  }, [rol, roomId, user])

  useEffect(() => {
    if (subtitulosRef.current) {
      subtitulosRef.current.scrollTop = subtitulosRef.current.scrollHeight
    }
  }, [subtitulos])

  const iniciar = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream
      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : ''
      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : {})
      recorderRef.current = recorder
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0 && wsRef.current?.readyState === WebSocket.OPEN) {
          wsRef.current.send(e.data)
        }
      }
      recorder.start(250)
      setGrabando(true)
      setPausado(false)
      setTiempo(0)
      intervalRef.current = setInterval(() => setTiempo((t) => t + 1), 1000)
    } catch {
      setEstadoWs('desconectado')
    }
  }, [])

  const pausar = useCallback(() => {
    recorderRef.current?.pause()
    setPausado(true)
  }, [])

  const reanudar = useCallback(() => {
    recorderRef.current?.resume()
    setPausado(false)
  }, [])

  const abrirModalFinalizar = useCallback(() => {
    setModalAbierto(true)
  }, [])

  const cancelarFinalizar = useCallback(() => {
    setModalAbierto(false)
  }, [])

  const confirmarFinalizar = useCallback((titulo) => {
    clearInterval(intervalRef.current)
    recorderRef.current?.stop()
    streamRef.current?.getTracks().forEach((t) => t.stop())
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ action: 'finalizar', titulo: titulo || null }))
    }
    setGrabando(false)
    setPausado(false)
    setModalAbierto(false)
  }, [])

  useEffect(() => {
    return () => clearInterval(intervalRef.current)
  }, [])

  if (determinando) {
    return (
      <main className="sala">
        <p style={{ padding: '2rem', textAlign: 'center', color: 'var(--muted)' }}>
          Verificando sala...
        </p>
      </main>
    )
  }

  if (claseFinalizada) {
    return (
      <main className="sala">
        <header className="sala-topbar">
          <button className="btn btn--ghost" onClick={() => window.location.hash = '#/dashboard'}>
            <IconoSalir size={18} /> <span>Salir</span>
          </button>
          <h1>Clase finalizada</h1>
          <div style={{ width: 60 }} />
        </header>
        <div style={{ padding: '2rem', textAlign: 'center' }}>
          <p>La clase ha sido guardada en tu historial.</p>
          {claseId && (
            <button
              className="btn btn--primary"
              style={{ marginTop: '1rem' }}
              onClick={() => window.location.hash = `#/historial/${claseId}`}
            >
              Ver en historial
            </button>
          )}
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
        <span className="sala-en-vivo">
          <span className="sala-en-vivo__dot" />
          EN VIVO
        </span>
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
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
                <line x1="9" y1="9" x2="15" y2="9"/>
                <line x1="9" y1="13" x2="15" y2="13"/>
                <line x1="9" y1="17" x2="13" y2="17"/>
              </svg>
              <span>Transcripción en Tiempo Real</span>
            </div>
            <div className="sala-subtitulos__tamano">
              <button onClick={() => setTamFuente((s) => Math.min(s + 2, 32))}>A+</button>
              <button onClick={() => setTamFuente((s) => Math.max(s - 2, 12))}>A−</button>
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
            {grabando && !pausado && <span><IconoMicrofono size={14} /> Escuchando al profesor...</span>}
            {grabando && pausado && <span style={{ color: 'var(--warning)' }}>Pausado</span>}
            {!grabando && <span style={{ color: 'var(--muted)' }}>{rol === 'listener' ? 'Conectado como oyente' : 'Listo para iniciar'}</span>}
          </div>
        </section>

        <section className="sala-video">
          <div className="sala-video__player">
            {conceptoClave && (
              <div className="concepto-card">
                <div className="concepto-card__label">TRADUCIENDO CONCEPTO CLAVE</div>
                <div className="concepto-card__value">
                  <IconoMano size={20} />
                  <span>{conceptoClave.texto_visible}</span>
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

      {rol === 'emitter' && (
        <footer className="sala-bottombar">
          <div className="sala-estado">
            <div className="sala-estado__label">Estado del Sistema</div>
            <div className="sala-estado__sub">
              <IconoCheck size={12} /> Audio y video sincronizados
            </div>
          </div>
          <div className="sala-controles">
            {!grabando ? (
              <button className="btn btn--ghost-pause" onClick={iniciar}>
                <IconoMicrofono size={18} /> Iniciar Transmisión
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
