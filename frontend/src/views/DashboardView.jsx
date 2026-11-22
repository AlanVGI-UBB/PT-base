import { useEffect, useState } from 'react'
import { fetchCursosUsuario, fetchSalaEstado } from '../api/cliente'
import Header from '../components/Header'

const IconoMicrofono = ({ size = 18 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
    <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
    <line x1="12" y1="19" x2="12" y2="23"/>
    <line x1="8" y1="23" x2="16" y2="23"/>
  </svg>
)

const IconoHistorial = ({ size = 16 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/>
    <path d="M3 3v5h5"/>
    <path d="M12 7v5l4 2"/>
  </svg>
)

export default function DashboardView({ user, onLogout, theme, onToggleTheme }) {
  const [cursos, setCursos] = useState([])
  const [estados, setEstados] = useState({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [recarga, setRecarga] = useState(0)

  useEffect(() => {
    if (!user) return
    setLoading(true)
    setError('')
    fetchCursosUsuario()
      .then(async (data) => {
        setCursos(data)
        setLoading(false)
        const map = {}
        await Promise.all(
          data.map(async (c) => {
            const roomId = `${c.cod_ramo}-${c.seccion}`
            const estado = await fetchSalaEstado(roomId).catch(() => ({ activa: false }))
            map[roomId] = Boolean(estado.activa)
          })
        )
        setEstados(map)
      })
      .catch((e) => {
        setLoading(false)
        setError(e.message || 'Error al cargar tus asignaturas')
      })
  }, [user, recarga])

  const irASala = (roomId) => {
    window.location.hash = `#/sala/${roomId}`
  }

  const claseActual = cursos[0]
  const otrasAsignaturas = cursos.slice(1)
  const roomClaseActual = claseActual ? `${claseActual.cod_ramo}-${claseActual.seccion}` : null
  const claseActiva = roomClaseActual ? Boolean(estados[roomClaseActual]) : false

  return (
    <>
      <Header
        activeTab="home"
        user={user}
        onLogout={onLogout}
        theme={theme}
        onToggleTheme={onToggleTheme}
      />

      <main className="vista">
        <header className="vista__intro">
          <div>
            <h1 className="vista__titulo">Tus asignaturas</h1>
            <p className="vista__subtitulo">
              Accede a tus salas en vivo o revisa tus transcripciones guardadas.
            </p>
          </div>
          <button
            type="button"
            className="btn btn--outline"
            onClick={() => { window.location.hash = '#/historial' }}
          >
            <IconoHistorial size={16} />
            <span>Historial de clases</span>
          </button>
        </header>

        {loading ? (
          <p className="dashboard__vacio">Cargando tus asignaturas...</p>
        ) : error ? (
          <div className="dashboard__vacio">
            <p>{error}</p>
            <button
              type="button"
              className="btn btn--outline"
              style={{ marginTop: '1rem' }}
              onClick={() => setRecarga((r) => r + 1)}
            >
              Reintentar
            </button>
          </div>
        ) : !claseActual ? (
          <p className="dashboard__vacio">No tienes asignaturas inscritas.</p>
        ) : (
          <>
            <section className="seccion-bloque">
              <div className="seccion-bloque__label">CLASE ACTUAL</div>
              <article className="clase-actual">
                <div className="clase-actual__top">
                  <div className="clase-actual__meta">
                    <span className="code-pill">{claseActual.cod_ramo}</span>
                    <span className="clase-actual__seccion">Sección {claseActual.seccion}</span>
                  </div>
                  <h2 className="clase-actual__titulo">{claseActual.nombre}</h2>
                </div>

                <div className="clase-actual__footer">
                  <div className={`clase-actual__estado ${claseActiva ? 'clase-actual__estado--vivo' : ''}`}>
                    <span className={`estado-dot ${claseActiva ? 'estado-dot--vivo' : ''}`} />
                    <span>{claseActiva ? 'En vivo' : 'Sin clase activa'}</span>
                  </div>

                  {(claseActiva || claseActual.puede_capturar) && (
                    <button
                      type="button"
                      className="btn btn--primary"
                      onClick={() => irASala(roomClaseActual)}
                    >
                      <IconoMicrofono size={17} />
                      <span>{claseActiva ? 'Entrar a la clase' : 'Iniciar transmisión de clase'}</span>
                    </button>
                  )}
                </div>
              </article>
            </section>

            {otrasAsignaturas.length > 0 && (
              <section className="seccion-bloque">
                <div className="seccion-bloque__label">OTRAS ASIGNATURAS</div>
                <div className="asignaturas__grid">
                  {otrasAsignaturas.map((c) => {
                    const roomId = `${c.cod_ramo}-${c.seccion}`
                    const activa = Boolean(estados[roomId])
                    return (
                      <article key={roomId} className="asignatura-card">
                        <div className="asignatura-card__head">
                          <span className="code-pill">{c.cod_ramo} · Sección {c.seccion}</span>
                          <h3 className="asignatura-card__titulo">{c.nombre}</h3>
                        </div>
                        <div className="asignatura-card__footer">
                          <span className={`asignatura-card__estado ${activa ? 'clase-actual__estado--vivo' : ''}`}>
                            <span className={`estado-dot ${activa ? 'estado-dot--vivo' : ''}`} />
                            <span>{activa ? 'En vivo' : 'Sin clase activa'}</span>
                          </span>
                          {(activa || c.puede_capturar) && (
                            <button
                              type="button"
                              className="btn btn--outline btn--sm"
                              onClick={() => irASala(roomId)}
                            >
                              {activa ? 'Entrar a la clase' : 'Iniciar'}
                            </button>
                          )}
                        </div>
                      </article>
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
