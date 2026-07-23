import { useEffect, useState } from 'react'
import { useAuth } from './hooks/useAuth'
import LoginView from './views/LoginView'
import DashboardView from './views/DashboardView'
import SalaView from './views/SalaView'
import HistorialView from './views/HistorialView'
import ClaseDetailView from './views/ClaseDetailView'
import './App.css'

export default function App() {
  const { user, login, loading, logout } = useAuth()
  const [hash, setHash] = useState(window.location.hash)

  useEffect(() => {
    const handler = () => setHash(window.location.hash)
    window.addEventListener('hashchange', handler)
    return () => window.removeEventListener('hashchange', handler)
  }, [])

  if (loading) {
    return <main className="vista"><p className="dashboard__vacio">Cargando...</p></main>
  }

  if (!user) return <LoginView onLogin={login} />

  if (hash.startsWith('#/sala/')) {
    const roomId = hash.replace('#/sala/', '')
    return <SalaView roomId={roomId} user={user} onVolver={() => window.location.hash = '#/dashboard'} />
  }

  if (hash.startsWith('#/historial/')) {
    return <ClaseDetailView user={user} />
  }

  if (hash === '#/historial') {
    return <HistorialView user={user} />
  }

  return (
    <DashboardView
      user={user}
      onLogout={logout}
      onIrSala={(roomId) => { window.location.hash = `#/sala/${roomId}` }}
    />
  )
}
