import { API_URL, expulsarSesion, getToken } from './cliente'

const cache = new Map()
const enCurso = new Map()
let generacion = 0

export async function obtenerClip(url) {
  if (!url) return null
  if (cache.has(url)) return cache.get(url)
  if (enCurso.has(url)) return enCurso.get(url)

  const genActual = generacion
  const fullUrl = url.startsWith('http') ? url : `${API_URL}${url}`
  const promesa = (async () => {
    const headers = {}
    const token = getToken()
    if (token) headers.Authorization = `Bearer ${token}`
    const resp = await fetch(fullUrl, { headers })
    if (resp.status === 401) {
      expulsarSesion()
      throw new Error('Sesión expirada')
    }
    if (!resp.ok) {
      throw new Error(`Error al descargar clip (${resp.status})`)
    }
    const blob = await resp.blob()
    const objectUrl = URL.createObjectURL(blob)
    if (genActual !== generacion) {
      URL.revokeObjectURL(objectUrl)
      return null
    }
    cache.set(url, objectUrl)
    return objectUrl
  })().finally(() => {
    if (genActual === generacion) {
      enCurso.delete(url)
    }
  })

  enCurso.set(url, promesa)
  return promesa
}

export function precargar(glosario) {
  if (!Array.isArray(glosario)) return
  for (const termino of glosario) {
    if (!termino?.video_url || termino.estado === 'retirado') continue
    obtenerClip(termino.video_url).catch(() => {})
  }
}

export function liberarClips() {
  generacion += 1
  for (const objectUrl of cache.values()) {
    URL.revokeObjectURL(objectUrl)
  }
  cache.clear()
  enCurso.clear()
}
