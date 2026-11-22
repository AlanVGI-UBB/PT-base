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

export function precargar(glosario, concurrencia = 4) {
  if (!Array.isArray(glosario)) return
  const urls = glosario
    .filter((termino) => termino?.video_url && termino.estado !== 'retirado')
    .map((termino) => termino.video_url)
  if (urls.length === 0) return

  const genActual = generacion
  let indice = 0
  const worker = async () => {
    while (indice < urls.length && genActual === generacion) {
      const url = urls[indice]
      indice += 1
      await obtenerClip(url).catch(() => {})
    }
  }
  const n = Math.min(concurrencia, urls.length)
  for (let i = 0; i < n; i += 1) {
    worker()
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
