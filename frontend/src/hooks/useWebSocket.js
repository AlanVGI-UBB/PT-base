import { useEffect, useRef, useState, useCallback } from 'react'

export function useWebSocket(url, { onMessage, onOpen, onClose } = {}) {
  const wsRef = useRef(null)
  const [estado, setEstado] = useState('desconectado')
  const reconnectRef = useRef(null)
  const aliveRef = useRef(false)

  const conectar = useCallback(() => {
    if (!url) return
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) return
    aliveRef.current = true
    const ws = new WebSocket(url)
    wsRef.current = ws
    ws.onopen = () => {
      setEstado('conectado')
      onOpen?.()
    }
    ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data)
        onMessage?.(data)
      } catch {
        onMessage?.({ type: 'raw', text: e.data })
      }
    }
    ws.onclose = () => {
      setEstado('desconectado')
      onClose?.()
      if (aliveRef.current) {
        reconnectRef.current = setTimeout(conectar, 3000)
      }
    }
  }, [url])

  useEffect(() => {
    conectar()
    return () => {
      aliveRef.current = false
      clearTimeout(reconnectRef.current)
      wsRef.current?.close()
    }
  }, [conectar])

  return {
    ws: wsRef,
    estado,
    send: (data) => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(data)
      }
    },
    enviar: (texto) => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(texto)
      }
    },
  }
}
