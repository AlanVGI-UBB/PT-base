const API_BASE = import.meta.env.VITE_API_URL
const API_URL = API_BASE !== undefined ? API_BASE : 'http://localhost:8000'
const TOKEN_KEY = 'puente_lsch_auth'

export function getToken() {
  try {
    const data = JSON.parse(localStorage.getItem(TOKEN_KEY))
    return data?.token || null
  } catch {
    return null
  }
}

export function expulsarSesion(mensaje = 'Sesión expirada, inicia sesión nuevamente') {
  localStorage.removeItem(TOKEN_KEY)
  sessionStorage.setItem('puente_auth_msg', mensaje)
  window.dispatchEvent(new Event('puente-auth-expired'))
}

export function normalizarRut(rut) {
  const limpio = (rut || '').replace(/[.\-\s]/g, '')
  if (!/^\d{7,8}[0-9kK]$/.test(limpio)) return null
  const cuerpo = limpio.slice(0, -1)
  const dv = limpio.slice(-1).toUpperCase()
  const suma = [...cuerpo].reverse().reduce((acc, d, i) => acc + Number(d) * (2 + (i % 6)), 0)
  const dvEsperado = 11 - (suma % 11)
  const dvCalculado = dvEsperado === 11 ? '0' : dvEsperado === 10 ? 'K' : String(dvEsperado)
  return dv === dvCalculado ? `${cuerpo}-${dv}` : null
}

async function peticion(url, opciones = {}) {
  const headers = { ...(opciones.headers || {}) }
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`
  const resp = await fetch(`${API_URL}${url}`, { ...opciones, headers })
  if (!resp.ok) {
    if (resp.status === 401) expulsarSesion()
    const err = await resp.json().catch(() => ({}))
    const error = new Error(err.detail || 'Error de red o del servidor')
    error.status = resp.status
    throw error
  }
  return resp.json()
}

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

export async function fetchCursosUsuario() {
  return peticion('/api/cursos')
}

export async function fetchUsuario() {
  return peticion('/api/auth/usuario/me')
}

export async function fetchGlosario(cursoId) {
  return peticion(`/api/cursos/${cursoId}/glosario`)
}

export async function fetchSalaEstado(roomId) {
  return peticion(`/api/salas/${roomId}/estado`)
}

export async function fetchHistorial() {
  return peticion('/api/historial')
}

export async function fetchHistorialDetalle(claseId) {
  return peticion(`/api/historial/${claseId}`)
}

export { API_URL }
