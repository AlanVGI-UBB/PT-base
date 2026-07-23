import { useEffect, useState } from 'react'
import { fetchCursosUsuario, fetchSalaEstado } from '../api/cliente'
import Header from '../components/Header'

const IconoMicrofono = ({ size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
    <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
    <line x1="12" y1="19" x2="12" y2="23"/>
    <line x1="8" y1="23" x2="16" y2="23"/>
  </svg>
)

const IconoPlay = ({ size = 18 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polygon points="5 3 19 12 5 21 5 3"/>
  </svg>
)

const IconoReloj = ({ size = 18 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10"/>
    <polyline points="12 6 12 12 16 14"/>
  </svg>
)

const IconoHistorial = ({ size = 18 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/>
    <path d="M3 3v5h5"/>
    <path d="M12 7v5l4 2"/>
  </svg>
)

const formatRut = (rut) => {
  if (!rut) return ''
  const clean = rut.replace(/[.-]/g, '')
  if (clean.length < 2) return rut
  const dv = clean.slice(-1)
  const num = clean.slice(0, -1)
  return `${Number(num).toLocaleString('es-CL')}-${dv}`
}

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

  const irASala = (roomId) => {
    window.location.hash = `#/sala/${roomId}`
  }

  const claseActual = cursos[0]
  const otrasAsignaturas = cursos.slice(1)

  return (
    <>
      <Header activeTab="home" />

      <main className="vista">
        <section className="user-card">
          <div className="user-card__info">
            <div className="user-card__name">{user?.nombre} {user?.apellido}</div>
            <div className="user-card__rut">{formatRut(user?.rut)}</div>
          </div>
          <div className="user-card__actions">
            <span className="mic-badge">
              <span className="mic-badge__dot" />
              Micrófono Conectado
            </span>
            <button className="btn btn--ghost" onClick={() => window.location.hash = '#/historial'}>
              <IconoHistorial size={18} />
              <span>Historial de Clases</span>
            </button>
            <button className="btn btn--ghost btn--logout" onClick={onLogout} title="Cerrar sesión">
              Salir
            </button>
          </div>
        </section>

        {loading ? (
          <p className="dashboard__vacio">Cargando...</p>
        ) : !claseActual ? (
          <p className="dashboard__vacio">No tienes asignaturas inscritas.</p>
        ) : (
          <>
            <section className="clase-actual">
              <span className="clase-actual__badge">CLASE ACTUAL</span>
              <h1 className="clase-actual__titulo">
                {claseActual.cod_ramo} — {claseActual.nombre}
              </h1>
              <span className="clase-actual__seccion">Sección {claseActual.seccion}</span>
              <div className="clase-actual__actions">
                <button className="btn btn--primary" onClick={() => irASala(`${claseActual.cod_ramo}-${claseActual.seccion}`)}>
                  <IconoMicrofono size={20} />
                  <span>Iniciar Transmisión de Clase</span>
                </button>
              </div>
            </section>

            {otrasAsignaturas.length > 0 && (
              <section className="asignaturas">
                <h2 className="asignaturas__titulo">Todas mis Asignaturas</h2>
                <div className="asignaturas__grid">
                  {otrasAsignaturas.map((c) => {
                    const roomId = `${c.cod_ramo}-${c.seccion}`
                    return (
                      <div key={roomId} className="asignatura-card">
                        <div className="asignatura-card__head">
                          <h3 className="asignatura-card__titulo">
                            {c.cod_ramo} — {c.nombre}
                          </h3>
                          <span className="asignatura-card__seccion">Sección {c.seccion}</span>
                        </div>
                        <button className="btn btn--ghost-outline" onClick={() => irASala(roomId)}>
                          <IconoPlay size={18} />
                          <span>Iniciar</span>
                        </button>
                      </div>
                    )
                  })}
                </div>
              </section>
            )}
          </>
        )}
      </main>
    </>
  )
}
