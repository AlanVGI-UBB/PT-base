import { useEffect, useState } from 'react'
import { fetchHistorialDetalle } from '../api/cliente'
import ReplayPlayer from '../components/ReplayPlayer'
import SenaPlayer from '../components/SenaPlayer'

export default function ClaseDetailView({ user }) {
  const [clase, setClase] = useState(null)
  const [eventos, setEventos] = useState([])
  const [modo, setModo] = useState('apunte')
  const claseId = window.location.hash.split('/').pop()

  useEffect(() => {
    fetchHistorialDetalle(claseId)
      .then((data) => {
        setClase(data.clase)
        setEventos(data.eventos)
      })
      .catch(console.error)
  }, [claseId])

  if (!clase) {
    return (
      <main className="vista">
        <p>Cargando...</p>
        <button className="btn btn--volver" onClick={() => window.location.hash = '#/historial'}>Volver</button>
      </main>
    )
  }

  return (
    <main className="vista">
      <header className="vista__header">
        <h1>{clase.titulo || `${clase.cod_ramo} — ${clase.seccion}`}</h1>
        <button className="btn btn--volver" onClick={() => window.location.hash = '#/historial'}>Volver</button>
      </header>

      <div className="alumno__panel">
        <div className="alumno__controles">
          <span className="dashboard__nombre">
            {clase.titulo ? `${clase.curso_nombre} · Sección ${clase.seccion}` : clase.curso_nombre}
          </span>
          <div className="alumno__fuente">
            <button
              className={`btn ${modo === 'apunte' ? 'btn--profesor' : 'btn--fuente'}`}
              onClick={() => setModo('apunte')}
            >
              Apunte
            </button>
            <button
              className={`btn ${modo === 'replay' ? 'btn--profesor' : 'btn--fuente'}`}
              onClick={() => setModo('replay')}
            >
              Replay
            </button>
          </div>
        </div>

        {modo === 'apunte' ? (
          <div className="historial__apunte">
            {eventos
              .filter((e) => e.estable)
              .map((e, i) => {
                const senasParsed = typeof e.senas === 'string' ? JSON.parse(e.senas) : (e.senas || [])
                return (
                  <p key={i} className="historial__linea">
                    {e.texto}
                    {senasParsed.length > 0 && (
                      <span className="historial__sena-badge">{senasParsed.map((s) => s.texto_visible).join(', ')}</span>
                    )}
                  </p>
                )
              })
            }
          </div>
        ) : (
          <ReplayPlayer eventos={eventos} />
        )}
      </div>
    </main>
  )
}
