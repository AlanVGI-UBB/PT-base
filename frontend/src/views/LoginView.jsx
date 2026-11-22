import { useEffect, useRef, useState } from 'react'
import { loginRequest, normalizarRut } from '../api/cliente'
import ThemeToggle from '../components/ThemeToggle'

const IconoInstalar = ({ size = 16 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
    <polyline points="7 10 12 15 17 10"/>
    <line x1="12" y1="15" x2="12" y2="3"/>
  </svg>
)

const IconoMenu = ({ size = 15 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="1"/>
    <circle cx="19" cy="12" r="1"/>
    <circle cx="5" cy="12" r="1"/>
  </svg>
)

export default function LoginView({ onLogin, theme, onToggleTheme }) {
  const [rut, setRut] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [aviso, setAviso] = useState('')
  const [loading, setLoading] = useState(false)
  const [instalable, setInstalable] = useState(false)
  const [mostrarAyuda, setMostrarAyuda] = useState(false)
  const [standalone, setStandalone] = useState(false)
  const installEvent = useRef(null)

  useEffect(() => {
    const msg = sessionStorage.getItem('puente_auth_msg')
    if (msg) {
      setAviso(msg)
      sessionStorage.removeItem('puente_auth_msg')
    }
  }, [])

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
    setAviso('')
    const rutNorm = normalizarRut(rut)
    if (!rutNorm) {
      setError('RUT inválido. Verifica el formato (ej. 12.345.678-5).')
      return
    }
    setLoading(true)
    try {
      const data = await loginRequest(rutNorm, password)
      onLogin(data.rut, data.nombre, data.apellido, data.token)
    } catch (err) {
      setError(err.message)
    }
    setLoading(false)
  }

  return (
    <main className="login-page">
      <div className="login-page__top">
        <span className="login-page__brand">Puente LSCh</span>
        {onToggleTheme && <ThemeToggle theme={theme} onToggle={onToggleTheme} />}
      </div>

      <div className="login-page__center">
        <section className="login-card">
          <header className="login-card__head">
            <span className="eyebrow">APOYO EN AULA · LSCH</span>
            <h1>Iniciar sesión</h1>
            <p className="login__sub">Ingresa con tu RUT institucional para acceder a tus salas y apuntes.</p>
          </header>

          <form className="login__form" onSubmit={handleSubmit}>
            <label className="campo">
              <span>RUT</span>
              <input
                type="text"
                value={rut}
                onChange={(e) => setRut(e.target.value)}
                placeholder="12345678-5"
                autoComplete="username"
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
                autoComplete="current-password"
              />
            </label>
            {error && <div className="login__error" role="alert">{error}</div>}
            {aviso && <div className="login__aviso" role="status">{aviso}</div>}
            <button className="btn btn--primary btn--full" type="submit" disabled={loading}>
              {loading ? 'Ingresando...' : 'Ingresar'}
            </button>
          </form>

          {!standalone && (
            <div className="login__instalar">
              <button type="button" onClick={instalar} className="btn btn--outline btn--full">
                <IconoInstalar size={16} />
                <span>Instalar aplicación</span>
              </button>
              {mostrarAyuda && !instalable && (
                <div className="login__ayuda">
                  <IconoMenu size={15} />
                  <span>Abre el menú de tu navegador (⋮) y selecciona <strong>«Agregar a pantalla de inicio»</strong>.</span>
                </div>
              )}
            </div>
          )}
        </section>
      </div>
    </main>
  )
}
