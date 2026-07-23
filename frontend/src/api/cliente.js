const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export async function fetchCursos() {
  const resp = await fetch(`${API_URL}/api/cursos`)
  if (!resp.ok) throw new Error('Error al cargar cursos')
  return resp.json()
}

export async function fetchGlosario(cursoId) {
  const resp = await fetch(`${API_URL}/api/cursos/${cursoId}/glosario`)
  if (!resp.ok) throw new Error('Error al cargar glosario')
  return resp.json()
}

export async function crearSesion(cursoId) {
  const resp = await fetch(`${API_URL}/api/sesiones?curso_id=${cursoId}`, { method: 'POST' })
  if (!resp.ok) throw new Error('Error al crear sesión')
  return resp.json()
}

export { API_URL }
