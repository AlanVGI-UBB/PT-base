import { useEffect, useState } from 'react'
import Landing from './views/Landing'
import ProfesorView from './views/ProfesorView'
import AlumnoView from './views/AlumnoView'
import './App.css'

export default function App() {
  const [hash, setHash] = useState(window.location.hash)

  useEffect(() => {
    const handler = () => setHash(window.location.hash)
    window.addEventListener('hashchange', handler)
    return () => window.removeEventListener('hashchange', handler)
  }, [])

  if (hash === '#/profesor') return <ProfesorView />
  if (hash === '#/alumno') return <AlumnoView />
  return <Landing />
}
