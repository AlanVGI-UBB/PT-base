import { useState } from 'react'
import { loginRequest } from '../api/cliente'

export default function LoginView({ onLogin }) {
  const [rut, setRut] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

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
      </div>
    </main>
  )
}
