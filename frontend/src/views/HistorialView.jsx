import { useEffect, useState } from 'react'
import { fetchHistorial } from '../api/cliente'

export default function HistorialView({ user }) {
  const [clases, setClases] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!user) return
    fetchHistorial(user.rut)
      .then(setClases)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [user])

  const fmtDuracion = (ms) => {
    if (!ms) return '—'
    const m = Math.floor(ms / 60000)
    const s = Math.floor((ms % 60000) / 1000)
    return `${m}m ${s}s`
  }

  const fmtFecha = (iso) => {
    if (!iso) return '—'
    return new Date(iso).toLocaleString('es-CL')
  }

  return (
    <main className="vista">
      <header className="vista__header">
        <h1>Historial de clases</h1>
        <button className="btn btn--volver" onClick={() => window.location.hash = '#/dashboard'}>Volver</button>
      </header>

      {loading ? (
        <p className="dashboard__vacio">Cargando...</p>
      ) : clases.length === 0 ? (
        <p className="dashboard__vacio">No tienes clases guardadas.</p>
      ) : (
        <div className="historial__lista">
          {clases.map((c) => (
            <div
              key={c.id}
              className="dashboard__card"
              onClick={() => window.location.hash = `#/historial/${c.id}`}
              style={{ cursor: 'pointer' }}
            >
              <div className="dashboard__card-info">
                <span className="dashboard__codigo">{c.cod_ramo} — {c.seccion}</span>
                <span className="dashboard__nombre">
                  {c.titulo || c.curso_nombre}
                </span>
                <span style={{ color: 'var(--muted)', fontSize: '0.85rem' }}>{fmtFecha(c.fecha_inicio)}</span>
              </div>
              <span style={{ color: 'var(--muted)', fontSize: '0.85rem' }}>
                {fmtDuracion(c.duracion_ms)}
              </span>
            </div>
          ))}
        </div>
      )}
    </main>
  )
}
