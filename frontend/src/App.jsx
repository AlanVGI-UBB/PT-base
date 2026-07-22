import { useEffect, useRef, useState } from 'react'

const WS_URL = import.meta.env.VITE_WS_URL ?? 'ws://localhost:8000/ws/echo'

export default function App() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [connected, setConnected] = useState(false)
  const socketRef = useRef(null)

  useEffect(() => {
  const ws = new WebSocket(WS_URL)
  socketRef.current = ws

  ws.onopen = () => setConnected(true)
  ws.onclose = () => setConnected(false)
  ws.onerror = () => setConnected(false)
  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      setMessages((prev) => [...prev, data])
    } catch {
      setMessages((prev) => [...prev, { type: 'raw', text: event.data }])
    }
  }

  return () => ws.close()
}, [])

  const enviar = (e) => {
    e.preventDefault()
    const ws = socketRef.current
    if (!ws || ws.readyState !== WebSocket.OPEN || !input.trim()) return
    ws.send(input.trim())
    setInput('')
  }

  return (
    <main className="app">
      <header className="app__header">
        <h1>Puente LSCh</h1>
        <span className={`badge ${connected ? 'badge--ok' : 'badge--off'}`}>
          {connected ? 'Conectado' : 'Desconectado'}
        </span>
      </header>

      <section className="app__panel">
        <p className="app__hint">
          WebSocket de eco (SPEC-001). Envia un texto y verás la respuesta del backend.
        </p>

        <form className="app__form" onSubmit={enviar}>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Escribe un mensaje..."
            autoFocus
          />
          <button type="submit" disabled={!connected}>Enviar</button>
        </form>

        <ul className="app__messages">
          {messages.map((m, i) => (
            <li key={i} className="msg">
              <span className="msg__text">{m.text}</span>
              <span className="msg__ts">
                {m.echoed_at ?? m.received_at}
              </span>
            </li>
          ))}
        </ul>
      </section>
    </main>
  )
}