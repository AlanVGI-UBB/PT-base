import { useCallback, useEffect, useRef, useState } from 'react'

const ESPERAS = [3000, 6000, 12000, 24000]
const MAX_INTENTOS = 5

export function useWebSocket(url, { onMessage, onOpen, onClose } = {}) {
  const wsRef = useRef(null)
  const [estado, setEstado] = useState('desconectado')
  const [intentos, setIntentos] = useState(0)
  const aliveRef = useRef(false)
  const timeoutRef = useRef(null)
  const intentosRef = useRef(0)
  const handlersRef = useRef({ onMessage, onOpen, onClose })
  handlersRef.current = { onMessage, onOpen, onClose }

  const conectar = useCallback(() => {
    if (!url) return
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) return
    aliveRef.current = true
    const ws = new WebSocket(url)
    wsRef.current = ws
    ws.onopen = () => {
      intentosRef.current = 0
      setIntentos(0)
      setEstado('conectado')
      handlersRef.current.onOpen?.()
    }
    ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data)
        handlersRef.current.onMessage?.(data)
      } catch {
        handlersRef.current.onMessage?.({ type: 'raw', text: e.data })
      }
    }
    ws.onclose = () => {
      wsRef.current = null
      if (!aliveRef.current) {
        setEstado('cerrado')
        return
      }
      handlersRef.current.onClose?.()
      if (intentosRef.current >= MAX_INTENTOS) {
        setEstado('fallo')
        return
      }
      const espera = ESPERAS[intentosRef.current] ?? 24000
      intentosRef.current += 1
      setIntentos(intentosRef.current)
      setEstado('reconectando')
      timeoutRef.current = setTimeout(conectar, espera)
    }
  }, [url])

  useEffect(() => {
    conectar()
    return () => {
      aliveRef.current = false
      clearTimeout(timeoutRef.current)
      wsRef.current?.close()
      wsRef.current = null
    }
  }, [conectar])

  const reintentar = useCallback(() => {
    clearTimeout(timeoutRef.current)
    intentosRef.current = 0
    setIntentos(0)
    conectar()
  }, [conectar])

  const enviar = useCallback((data) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(data)
    }
  }, [])

  return {
    ws: wsRef,
    estado,
    intentos,
    enviar,
    reintentar,
  }
}
