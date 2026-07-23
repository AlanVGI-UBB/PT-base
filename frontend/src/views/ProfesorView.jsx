import { useCallback, useEffect, useRef, useState } from 'react'
import { useWebSocket } from '../hooks/useWebSocket'
import CursoSelector from '../components/CursoSelector'
import EstadoConexion from '../components/EstadoConexion'

const WS_URL = import.meta.env.VITE_WS_URL ?? 'ws://localhost:8000'

export default function ProfesorView() {
  const [cursoId, setCursoId] = useState(null)
  const [estado, setEstado] = useState('idle')
  const [error, setError] = useState(null)
  const [chunks, setChunks] = useState(0)
  const [tiempo, setTiempo] = useState(0)
  const recorderRef = useRef(null)
  const streamRef = useRef(null)
  const intervalRef = useRef(null)

  const wsUrl = cursoId ? `${WS_URL}/ws/profesor?curso_id=${cursoId}` : null
  const { ws, estado: wsEstado, send } = useWebSocket(wsUrl, {
    onOpen: () => {},
    onClose: () => setEstado('detenido'),
    onMessage: () => {},
  })

  const iniciar = useCallback(async () => {
    if (!cursoId) return
    setEstado('conectando')
    setError(null)
    setChunks(0)
    setTiempo(0)
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream
      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : ''
      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : {})
      recorderRef.current = recorder
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0 && ws.current?.readyState === WebSocket.OPEN) {
          ws.current.send(e.data)
          setChunks(c => c + 1)
        }
      }
      recorder.onerror = (e) => {
        setError('Error en la grabación')
        setEstado('detenido')
      }
      recorder.start(250)
      setEstado('grabando')
      intervalRef.current = setInterval(() => setTiempo(t => t + 1), 1000)
    } catch (err) {
      if (err.name === 'NotAllowedError') {
        setError('Permiso de micrófono denegado. Permite el acceso en la configuración del navegador.')
      } else if (err.name === 'NotFoundError') {
        setError('No se encontró micrófono conectado.')
      } else {
        setError(err.message)
      }
      setEstado('detenido')
    }
  }, [cursoId, ws])

  const detener = useCallback(() => {
    clearInterval(intervalRef.current)
    recorderRef.current?.stop()
    streamRef.current?.getTracks().forEach(t => t.stop())
    recorderRef.current = null
    streamRef.current = null
    setEstado('detenido')
  }, [])

  useEffect(() => {
    return () => {
      clearInterval(intervalRef.current)
      recorderRef.current?.stop()
      streamRef.current?.getTracks().forEach(t => t.stop())
    }
  }, [])

  const fmt = (s) => `${Math.floor(s / 60).toString().padStart(2, '0')}:${(s % 60).toString().padStart(2, '0')}`

  return (
    <main className="vista vista--profesor">
      <header className="vista__header">
        <h1>Profesor</h1>
        <button className="btn btn--volver" onClick={() => window.location.hash = ''}>Volver</button>
      </header>

      <div className="profesor__panel">
        <div className="profesor__controles">
          <label className="campo">
            <span>Curso</span>
            <CursoSelector onSelect={setCursoId} />
          </label>

          {estado !== 'grabando' ? (
            <button className="btn btn--iniciar" onClick={iniciar} disabled={!cursoId || wsEstado !== 'conectado'}>
              {wsEstado !== 'conectado' ? 'Conectando...' : 'Iniciar transcripción'}
            </button>
          ) : (
            <button className="btn btn--detener" onClick={detener}>
              Detener
            </button>
          )}
        </div>

        <EstadoConexion estado={wsEstado} />

        {estado === 'grabando' && (
          <div className="profesor__estado">
            <span className="badge badge--grabando">Grabando</span>
            <span className="profesor__tiempo">{fmt(tiempo)}</span>
            <span className="profesor__chunks">{chunks} chunks enviados</span>
          </div>
        )}

        {error && (
          <div className="profesor__error">{error}</div>
        )}
      </div>
    </main>
  )
}
