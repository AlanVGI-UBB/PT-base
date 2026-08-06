import { useEffect, useMemo, useState } from 'react'
import { fetchHistorial } from '../api/cliente'
import Header from '../components/Header'

const IconoBuscar = ({ size = 18 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="11" cy="11" r="8"/>
    <line x1="21" y1="21" x2="16.65" y2="16.65"/>
  </svg>
)

const IconoChevron = ({ size = 16 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="9 18 15 12 9 6"/>
  </svg>
)

const IconoPalabras = ({ size = 14 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="3" y1="6" x2="21" y2="6"/>
    <line x1="3" y1="12" x2="15" y2="12"/>
    <line x1="3" y1="18" x2="18" y2="18"/>
  </svg>
)

const IconoBookmark = ({ size = 14 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/>
  </svg>
)

const IconoPizarra = ({ size = 14 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="3" width="18" height="18" rx="2"/>
    <line x1="3" y1="9" x2="21" y2="9"/>
    <line x1="9" y1="21" x2="9" y2="9"/>
  </svg>
)

const MESES = [
  'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
  'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
]

const formatearMes = (iso) => {
  if (!iso) return ''
  const d = new Date(iso)
  return `${MESES[d.getMonth()]} ${d.getFullYear()}`
}

const claveMes = (iso) => {
  if (!iso) return ''
  const d = new Date(iso)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}

const etiquetaMes = (clave) => {
  const [anio, mes] = clave.split('-')
  return `${MESES[Number(mes) - 1]} ${anio}`
}

const formatearDiaHora = (iso) => {
  if (!iso) return { dia: '—', hora: '—' }
  const d = new Date(iso)
  const dia = `${d.getDate().toString().padStart(2, '0')} ${MESES[d.getMonth()].slice(0, 3)}`
  let hora = d.toLocaleTimeString('es-CL', { hour: '2-digit', minute: '2-digit', hour12: true })
  return { dia, hora }
}

const truncar = (texto, max) => {
  if (!texto) return ''
  if (texto.length <= max) return texto
  return texto.slice(0, max).trim() + '...'
}

const tipoMeta = (c) => {
  const segs = Math.floor((c.duracion_ms || 0) / 60000)
  if (segs >= 30) return { icono: 'pizarra', label: 'Pizarras' }
  if (segs >= 10) return { icono: 'bookmark', label: 'Marcador' }
  return { icono: 'palabras', label: `${(c.palabras || 0).toLocaleString('es-CL')} palabras` }
}

const IconoMeta = ({ tipo }) => {
  if (tipo === 'pizarra') return <IconoPizarra size={14} />
  if (tipo === 'bookmark') return <IconoBookmark size={14} />
  return <IconoPalabras size={14} />
}

export default function HistorialView({ user }) {
  const [clases, setClases] = useState([])
  const [loading, setLoading] = useState(true)
  const [busqueda, setBusqueda] = useState('')
  const [filtroAsig, setFiltroAsig] = useState('Todas las Asignaturas')
  const [filtroFecha, setFiltroFecha] = useState('Todas las fechas')

  useEffect(() => {
    if (!user) return
    fetchHistorial()
      .then(setClases)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [user])

  const clasesFiltradas = useMemo(() => {
    return clases.filter((c) => {
      const titulo = (c.titulo || c.curso_nombre || '').toLowerCase()
      const ramo = (c.cod_ramo || '').toLowerCase()
      const search = busqueda.toLowerCase()
      const matchBusqueda = !search ||
        titulo.includes(search) ||
        ramo.includes(search) ||
        (c.preview || '').toLowerCase().includes(search)
      const matchAsig = filtroAsig === 'Todas las Asignaturas' || ramo === filtroAsig
      const matchFecha = filtroFecha === 'Todas las fechas' || claveMes(c.fecha_inicio) === filtroFecha
      return matchBusqueda && matchAsig && matchFecha
    })
  }, [clases, busqueda, filtroAsig, filtroFecha])

  const grupos = useMemo(() => {
    const map = new Map()
    clasesFiltradas.forEach((c) => {
      const key = formatearMes(c.fecha_inicio)
      if (!map.has(key)) map.set(key, [])
      map.get(key).push(c)
    })
    return Array.from(map.entries())
  }, [clasesFiltradas])

  const asignaturas = useMemo(() => {
    const set = new Set(clases.map((c) => c.cod_ramo).filter(Boolean))
    return ['Todas las Asignaturas', ...Array.from(set).sort()]
  }, [clases])

  const meses = useMemo(() => {
    const set = new Set(clases.map((c) => claveMes(c.fecha_inicio)).filter(Boolean))
    return ['Todas las fechas', ...Array.from(set).sort().reverse()]
  }, [clases])

  return (
    <>
      <Header activeTab="history" user={user} />

      <main className="historial-page">
        <header className="historial-page__intro">
          <h1 className="historial-page__titulo">Historial de Clases</h1>
          <p className="historial-page__subtitulo">
            Revisa transcripciones pasadas, notas guardadas y momentos destacados de
            tus sesiones anteriores. Usa los filtros para encontrar clases específicas rápidamente.
          </p>
        </header>

        <div className="historial-page__filtros">
          <div className="historial-search">
            <IconoBuscar size={18} />
            <input
              type="text"
              value={busqueda}
              onChange={(e) => setBusqueda(e.target.value)}
              placeholder="Buscar por título, asignatura o palabras clave..."
            />
          </div>

          <div className="historial-filtros__derecha">
            <select
              className="historial-filtro"
              value={filtroAsig}
              onChange={(e) => setFiltroAsig(e.target.value)}
              aria-label="Filtrar por asignatura"
            >
              {asignaturas.map((a) => (
                <option key={a} value={a}>{a}</option>
              ))}
            </select>

            <select
              className="historial-filtro historial-filtro--fecha"
              value={filtroFecha}
              onChange={(e) => setFiltroFecha(e.target.value)}
              aria-label="Filtrar por fecha"
            >
              {meses.map((m) => (
                <option key={m} value={m}>
                  {m === 'Todas las fechas' ? m : etiquetaMes(m)}
                </option>
              ))}
            </select>
          </div>
        </div>

        {loading ? (
          <p className="dashboard__vacio">Cargando...</p>
        ) : clases.length === 0 ? (
          <p className="dashboard__vacio">No tienes clases guardadas aún.</p>
        ) : clasesFiltradas.length === 0 ? (
          <p className="dashboard__vacio">No hay clases que coincidan con tu búsqueda.</p>
        ) : (
          <div className="historial-grupos">
            {grupos.map(([mes, items]) => (
              <section key={mes} className="historial-grupo">
                <h2 className="historial-grupo__titulo">{mes}</h2>
                <div className="historial-grupo__cards">
                  {items.map((c) => {
                    const { dia, hora } = formatearDiaHora(c.fecha_inicio)
                    const meta = tipoMeta(c)
                    const titulo = c.titulo || c.curso_nombre
                    const descripcion = truncar(c.preview || 'Sin transcripción disponible.', 180)
                    return (
                      <article
                        key={c.id}
                        className="historial-card"
                        onClick={() => window.location.hash = `#/historial/${c.id}`}
                      >
                        <header className="historial-card__head">
                          <span className="historial-card__asignatura">
                            <span className={`historial-card__dot historial-card__dot--${c.cod_ramo}`} />
                            {c.curso_nombre}
                          </span>
                          <div className="historial-card__fecha">
                            <div className="historial-card__dia">{dia}</div>
                            <div className="historial-card__hora">{hora}</div>
                          </div>
                        </header>

                        <h3 className="historial-card__titulo">{truncar(titulo, 32)}</h3>
                        <p className="historial-card__desc">{descripcion}</p>

                        <footer className="historial-card__foot">
                          <span className="historial-card__meta">
                            <IconoMeta tipo={meta.icono} />
                            <span>{meta.label}</span>
                          </span>
                          <span className="historial-card__ver">
                            Ver clase <IconoChevron size={14} />
                          </span>
                        </footer>
                      </article>
                    )
                  })}
                </div>
              </section>
            ))}
          </div>
        )}
      </main>
    </>
  )
}
