import { useEffect, useState } from 'react'
import { useAuth } from './hooks/useAuth'
import { useTheme } from './hooks/useTheme'
import LoginView from './views/LoginView'
import DashboardView from './views/DashboardView'
import SalaView from './views/SalaView'
import HistorialView from './views/HistorialView'
import ClaseDetailView from './views/ClaseDetailView'
import './App.css'

export default function App() {
  const { user, login, loading, logout } = useAuth()
  const { theme, toggleTheme } = useTheme()
  const [hash, setHash] = useState(window.location.hash)

  useEffect(() => {
    const handler = () => setHash(window.location.hash)
    window.addEventListener('hashchange', handler)
    return () => window.removeEventListener('hashchange', handler)
  }, [])

  if (loading) {
    return <main className="vista"><p className="dashboard__vacio">Cargando...</p></main>
  }

  if (!user) return <LoginView onLogin={login} theme={theme} onToggleTheme={toggleTheme} />

  if (hash.startsWith('#/sala/')) {
    const roomId = hash.replace('#/sala/', '')
    return (
      <SalaView
        roomId={roomId}
        user={user}
        theme={theme}
        onToggleTheme={toggleTheme}
        onVolver={() => { window.location.hash = '#/dashboard' }}
      />
    )
  }

  if (hash.startsWith('#/historial/')) {
    return <ClaseDetailView user={user} theme={theme} onToggleTheme={toggleTheme} />
  }

  if (hash === '#/historial') {
    return (
      <HistorialView
        user={user}
        onLogout={logout}
        theme={theme}
        onToggleTheme={toggleTheme}
      />
    )
  }

  return (
    <DashboardView
      user={user}
      onLogout={logout}
      theme={theme}
      onToggleTheme={toggleTheme}
    />
  )
}
