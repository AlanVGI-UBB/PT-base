import { useEffect, useRef, useState } from 'react'
import { loginRequest } from '../api/cliente'

const IconoInstalar = ({ size = 18 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
    <polyline points="7 10 12 15 17 10"/>
    <line x1="12" y1="15" x2="12" y2="3"/>
  </svg>
)

const IconoMenu = ({ size = 18 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="1"/>
    <circle cx="19" cy="12" r="1"/>
    <circle cx="5" cy="12" r="1"/>
  </svg>
)

export default function LoginView({ onLogin }) {
  const [rut, setRut] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [instalable, setInstalable] = useState(false)
  const [mostrarAyuda, setMostrarAyuda] = useState(false)
  const [standalone, setStandalone] = useState(false)
  const installEvent = useRef(null)

  useEffect(() => {
    const mq = window.matchMedia('(display-mode: standalone)')
    setStandalone(mq.matches)
    if (mq.matches) return

    const handler = (e) => {
      e.preventDefault()
      installEvent.current = e
      setInstalable(true)
    }
    window.addEventListener('beforeinstallprompt', handler)
    return () => window.removeEventListener('beforeinstallprompt', handler)
  }, [])

  const instalar = async () => {
    if (installEvent.current) {
      installEvent.current.prompt()
      const resultado = await installEvent.current.userChoice
      if (resultado.outcome === 'accepted') {
        setInstalable(false)
        installEvent.current = null
      }
    } else {
      setMostrarAyuda((v) => !v)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const data = await loginRequest(rut, password)
      onLogin(data.rut, data.nombre, data.apellido, data.token)
    } catch (err) {
      setError(err.message)
    }
    setLoading(false)
  }

  return (
    <main className="vista">
      <div className="login">
        <h1>Puente LSCh</h1>
        <p className="login__sub">Inicia sesión con tu RUT institucional</p>
        <form className="login__form" onSubmit={handleSubmit}>
          <label className="campo">
            <span>RUT</span>
            <input
              type="text"
              value={rut}
              onChange={(e) => setRut(e.target.value)}
              placeholder="12345678-9"
              autoFocus
            />
          </label>
          <label className="campo">
            <span>Contraseña</span>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
            />
          </label>
          {error && <div className="login__error">{error}</div>}
          <button className="btn btn--profesor" type="submit" disabled={loading}>
            {loading ? 'Ingresando...' : 'Ingresar'}
          </button>
        </form>

        {!standalone && (
          <div className="login__instalar">
            <button onClick={instalar} className="btn btn--fuente" style={{ width: '100%' }}>
              <IconoInstalar size={18} />
              Instalar aplicación
            </button>
            {mostrarAyuda && !instalable && (
              <div className="login__ayuda">
                <IconoMenu size={16} />
                <span>Abrí el menú de Chrome (⋮) y seleccioná <strong>"Agregar a pantalla de inicio"</strong></span>
              </div>
            )}
          </div>
        )}
      </div>
    </main>
  )
}
