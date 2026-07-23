import { useCallback, useEffect, useRef, useState } from 'react'
import { fetchSalaEstado } from '../api/cliente'
import Subtitulos from '../components/Subtitulos'
import SenaPlayer from '../components/SenaPlayer'
import EstadoConexion from '../components/EstadoConexion'
import ControlesEmisor from '../components/ControlesEmisor'

const WS_URL = import.meta.env.VITE_WS_URL ?? 'ws://localhost:8000'

export default function SalaView({ roomId, user, onVolver }) {
  const [rol, setRol] = useState(null)
  const [estadoWs, setEstadoWs] = useState('desconectado')
  const [subtitulos, setSubtitulos] = useState([])
  const [senas, setSenas] = useState([])
  const [grabando, setGrabando] = useState(false)
  const [pausado, setPausado] = useState(false)
  const [chunks, setChunks] = useState(0)
  const [tiempo, setTiempo] = useState(0)
  const [claseFinalizada, setClaseFinalizada] = useState(false)
  const [claseId, setClaseId] = useState(null)
  const wsRef = useRef(null)
  const recorderRef = useRef(null)
  const streamRef = useRef(null)
  const intervalRef = useRef(null)
  const [determinando, setDeterminando] = useState(true)

  // Determinar rol
  useEffect(() => {
    if (!roomId || !user) return
    fetchSalaEstado(roomId).then((estado) => {
      if (estado.activa) {
        setRol('listener')
      } else {
        setRol('emitter')
      }
      setDeterminando(false)
    })
  }, [roomId, user])

  // Conectar WebSocket cuando rol esté determinado
  useEffect(() => {
    if (!rol || !roomId || !user) return
    const token = JSON.parse(localStorage.getItem('puente_lsch_auth')).token
    const url = `${WS_URL}/ws/sala/${roomId}?rol=${rol}&token=${token}`
    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => setEstadoWs('conectado')
    ws.onclose = () => setEstadoWs('desconectado')
    ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data)
        if (data.type === 'segmento') {
          if (data.final) {
            setSubtitulos((prev) => [...prev, { id: data.segment_id, texto: data.texto, final: true }])
            if (data.senas && data.senas.length > 0) {
              setSenas(data.senas)
            }
          } else {
            setSubtitulos((prev) => {
              const copia = [...prev]
              const last = copia[copia.length - 1]
              if (last && !last.final) {
                copia[copia.length - 1] = { ...last, texto: data.texto }
              } else {
                copia.push({ id: data.segment_id, texto: data.texto, final: false })
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
          setChunks((c) => c + 1)
        }
      }
      recorder.start(250)
      setGrabando(true)
      setPausado(false)
      setChunks(0)
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

  const finalizar = useCallback(() => {
    clearInterval(intervalRef.current)
    recorderRef.current?.stop()
    streamRef.current?.getTracks().forEach((t) => t.stop())
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send('{"action":"finalizar"}')
    }
    setGrabando(false)
    setPausado(false)
  }, [])

  useEffect(() => {
    return () => {
      clearInterval(intervalRef.current)
    }
  }, [])

  if (determinando) {
    return (
      <main className="vista">
        <p>Verificando sala...</p>
      </main>
    )
  }

  if (claseFinalizada) {
    return (
      <main className="vista">
        <header className="vista__header">
          <h1>Clase finalizada</h1>
          <button className="btn btn--volver" onClick={() => window.location.hash = '#/dashboard'}>Volver</button>
        </header>
        <div className="profesor__panel">
          <p>La clase ha sido guardada en tu historial.</p>
          {claseId && (
            <button className="btn btn--profesor" onClick={() => window.location.hash = `#/historial/${claseId}`}>
              Ver en historial
            </button>
          )}
        </div>
      </main>
    )
  }

  return (
    <main className="vista">
      <header className="vista__header">
        <h1>Sala {roomId}</h1>
        <span className="badge badge--conectado">{rol === 'emitter' ? 'Emisor' : 'Oyente'}</span>
        <EstadoConexion estado={estadoWs} />
        <button className="btn btn--volver" onClick={onVolver}>Volver</button>
      </header>

      <div className="alumno__panel">
        {rol === 'emitter' && (
          <ControlesEmisor
            estado={grabando ? (pausado ? 'pausado' : 'grabando') : 'idle'}
            onIniciar={iniciar}
            onPausar={pausar}
            onReanudar={reanudar}
            onFinalizar={finalizar}
            tiempo={tiempo}
            chunks={chunks}
          />
        )}

        <div className="alumno__contenido">
          <div className="alumno__subtitulos">
            <Subtitulos items={subtitulos} />
          </div>
          <SenaPlayer senas={senas} />
        </div>
      </div>
    </main>
  )
}
