import { useCallback, useState } from 'react'
import { useWebSocket } from '../hooks/useWebSocket'
import CursoSelector from '../components/CursoSelector'
import Subtitulos from '../components/Subtitulos'
import SenaPlayer from '../components/SenaPlayer'
import EstadoConexion from '../components/EstadoConexion'

const WS_URL = import.meta.env.VITE_WS_URL ?? 'ws://localhost:8000'

export default function AlumnoView() {
  const [cursoId, setCursoId] = useState(null)
  const [subtitulos, setSubtitulos] = useState([])
  const [senasActivas, setSenasActivas] = useState([])
  const [tamFuente, setTamFuente] = useState(1.4)

  const wsUrl = cursoId ? `${WS_URL}/ws/alumno/${cursoId}` : null

  const onMessage = useCallback((evento) => {
    if (evento.type !== 'segmento') return
    if (evento.final) {
      setSubtitulos(prev => [...prev, { id: evento.segment_id, texto: evento.texto, final: true }])
      if (evento.senas && evento.senas.length > 0) {
        setSenasActivas(evento.senas)
      }
    } else {
      setSubtitulos(prev => {
        const copia = [...prev]
        const last = copia[copia.length - 1]
        if (last && !last.final) {
          copia[copia.length - 1] = { ...last, texto: evento.texto }
        } else {
          copia.push({ id: evento.segment_id, texto: evento.texto, final: false })
        }
        return copia
      })
    }
  }, [])

  const { estado } = useWebSocket(wsUrl ?? 'ws://0.0.0.0', { onMessage })

  const masGrande = () => setTamFuente(s => Math.min(s + 0.2, 3))
  const masChico = () => setTamFuente(s => Math.max(s - 0.2, 0.8))

  return (
    <main className="vista vista--alumno">
      <header className="vista__header">
        <h1>Alumno</h1>
        <button className="btn btn--volver" onClick={() => window.location.hash = ''}>Volver</button>
      </header>

      <div className="alumno__panel">
        <div className="alumno__controles">
          <label className="campo">
            <span>Curso</span>
            <CursoSelector onSelect={setCursoId} />
          </label>
          <div className="alumno__fuente">
            <button onClick={masChico} className="btn btn--fuente">A-</button>
            <button onClick={masGrande} className="btn btn--fuente">A+</button>
          </div>
          <EstadoConexion estado={estado} />
        </div>

        <div className="alumno__contenido">
          <div className="alumno__subtitulos" style={{ fontSize: `${tamFuente}rem` }}>
            <Subtitulos items={subtitulos} />
          </div>
          <SenaPlayer senas={senasActivas} />
        </div>
      </div>
    </main>
  )
}
