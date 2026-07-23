import { useEffect, useState } from 'react'
import { fetchCursosUsuario, fetchSalaEstado } from '../api/cliente'

export default function DashboardView({ user, onIrSala, onLogout }) {
  const [cursos, setCursos] = useState([])
  const [estados, setEstados] = useState({})
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!user) return
    fetchCursosUsuario(user.rut)
      .then(async (data) => {
        setCursos(data)
        setLoading(false)
        const map = {}
        await Promise.all(
          data.map(async (c) => {
            const roomId = `${c.cod_ramo}-${c.seccion}`
            const estado = await fetchSalaEstado(roomId)
            map[roomId] = estado.activa
          })
        )
        setEstados(map)
      })
      .catch(() => setLoading(false))
  }, [user])

  return (
    <main className="vista">
      <header className="vista__header">
        <h1>Dashboard</h1>
        <span className="badge badge--conectado">{user?.nombre} {user?.apellido}</span>
        <button className="btn btn--volver" onClick={onLogout}>Salir</button>
      </header>

      <div className="dashboard">
        <div className="dashboard__tabs">
          <button className="btn btn--profesor">Mis clases</button>
          <button className="btn btn--fuente" onClick={() => window.location.hash = '#/historial'}>Historial</button>
        </div>

        {loading ? (
          <p className="dashboard__vacio">Cargando...</p>
        ) : cursos.length === 0 ? (
          <p className="dashboard__vacio">No tienes asignaturas inscritas.</p>
        ) : (
          <div className="dashboard__cards">
            {cursos.map((c) => {
              const roomId = `${c.cod_ramo}-${c.seccion}`
              const vivo = estados[roomId] || false
              return (
                <div key={roomId} className="dashboard__card">
                  <div className="dashboard__card-info">
                    <span className="dashboard__codigo">{c.cod_ramo} — {c.seccion}</span>
                    <span className="dashboard__nombre">{c.nombre}</span>
                  </div>
                  <div className="dashboard__card-accion">
                    <span className={`badge ${vivo ? 'badge--conectado' : 'badge--desconectado'}`}>
                      {vivo ? 'En vivo' : 'Sin clase activa'}
                    </span>
                    <button className="btn btn--profesor" onClick={() => onIrSala(roomId, true)}>
                      Entrar
                    </button>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </main>
  )
}
