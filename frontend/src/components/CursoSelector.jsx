import { useEffect, useRef, useState } from 'react'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export default function CursoSelector({ onSelect }) {
  const [cursos, setCursos] = useState([])
  const [seleccionado, setSeleccionado] = useState('')
  const mounted = useRef(false)

  useEffect(() => {
    if (mounted.current) return
    mounted.current = true
    fetch(`${API_URL}/api/cursos`)
      .then(r => r.json())
      .then(data => {
        setCursos(data)
        if (data.length > 0) {
          setSeleccionado(String(data[0].id))
          onSelect?.(data[0].id)
        }
      })
      .catch(console.error)
  }, [])

  const handleChange = (e) => {
    const id = Number(e.target.value)
    setSeleccionado(e.target.value)
    onSelect?.(id)
  }

  return (
    <select
      value={seleccionado}
      onChange={handleChange}
      className="selector-curso"
    >
      {cursos.length === 0 && <option value="">Cargando cursos...</option>}
      {cursos.map(c => (
        <option key={c.id} value={c.id}>{c.nombre}</option>
      ))}
    </select>
  )
}
