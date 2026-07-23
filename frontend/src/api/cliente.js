const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export async function loginRequest(rut, password) {
  const resp = await fetch(`${API_URL}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ rut, password }),
  })
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}))
    throw new Error(err.detail || 'Error al iniciar sesión')
  }
  return resp.json()
}

export async function fetchCursos() {
  const resp = await fetch(`${API_URL}/api/cursos`)
  if (!resp.ok) throw new Error('Error al cargar cursos')
  return resp.json()
}

export async function fetchCursosUsuario(rut) {
  const resp = await fetch(`${API_URL}/api/cursos?rut=${rut}`)
  if (!resp.ok) throw new Error('Error al cargar cursos')
  return resp.json()
}

export async function fetchUsuario(rut) {
  const resp = await fetch(`${API_URL}/api/auth/usuario/me?rut=${rut}`)
  if (!resp.ok) throw new Error('Error al cargar usuario')
  return resp.json()
}

export async function fetchGlosario(cursoId) {
  const resp = await fetch(`${API_URL}/api/cursos/${cursoId}/glosario`)
  if (!resp.ok) throw new Error('Error al cargar glosario')
  return resp.json()
}

export async function fetchSalaEstado(roomId) {
  const resp = await fetch(`${API_URL}/api/salas/${roomId}/estado`)
  if (!resp.ok) return { activa: false }
  return resp.json()
}

export async function fetchHistorial(rut) {
  const resp = await fetch(`${API_URL}/api/historial?rut=${rut}`)
  if (!resp.ok) throw new Error('Error al cargar historial')
  return resp.json()
}

export async function fetchHistorialDetalle(claseId) {
  const resp = await fetch(`${API_URL}/api/historial/${claseId}`)
  if (!resp.ok) throw new Error('Error al cargar detalle')
  return resp.json()
}

export { API_URL }
