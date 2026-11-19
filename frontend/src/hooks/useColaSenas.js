import { useCallback, useRef, useState } from 'react'

export const MAX_PENDIENTES = 3
export const VENTANA_REPETIDA_MS = 20000

function claveConcepto(sena) {
  return sena?.termino_id ?? sena?.texto_visible ?? ''
}

export function useColaSenas() {
  const colaRef = useRef({
    actual: null,
    pendientes: [],
    omitidas: 0,
    playId: 0,
    recientes: new Map(),
  })

  const [estado, setEstado] = useState({
    actual: null,
    pendientes: [],
    omitidas: 0,
    playId: 0,
  })

  const sincronizar = useCallback(() => {
    const c = colaRef.current
    setEstado({
      actual: c.actual,
      pendientes: [...c.pendientes],
      omitidas: c.omitidas,
      playId: c.playId,
    })
  }, [])

  const encolar = useCallback((senas) => {
    if (!senas || senas.length === 0) return
    const c = colaRef.current
    const ahora = Date.now()

    for (const [clave, ts] of c.recientes.entries()) {
      if (ahora - ts >= VENTANA_REPETIDA_MS) {
        c.recientes.delete(clave)
      }
    }

    let cambio = false
    for (const s of senas) {
      const clave = claveConcepto(s)
      if (!clave) continue

      const esActual = c.actual && claveConcepto(c.actual) === clave
      const enCola = c.pendientes.some((p) => claveConcepto(p) === clave)
      const tsReciente = c.recientes.get(clave)
      const esReciente = tsReciente !== undefined && ahora - tsReciente < VENTANA_REPETIDA_MS

      if (esActual || enCola || esReciente) {
        continue
      }

      if (!c.actual) {
        c.actual = s
        c.playId += 1
      } else if (c.pendientes.length < MAX_PENDIENTES) {
        c.pendientes.push(s)
      } else {
        c.pendientes.shift()
        c.pendientes.push(s)
        c.omitidas += 1
      }
      cambio = true
    }

    if (cambio) {
      sincronizar()
    }
  }, [sincronizar])

  const alTerminar = useCallback(() => {
    const c = colaRef.current
    if (c.actual) {
      c.recientes.set(claveConcepto(c.actual), Date.now())
    }
    if (c.pendientes.length > 0) {
      c.actual = c.pendientes.shift()
      c.playId += 1
    } else {
      c.actual = null
    }
    sincronizar()
  }, [sincronizar])

  const limpiar = useCallback(() => {
    const c = colaRef.current
    c.actual = null
    c.pendientes = []
    c.omitidas = 0
    c.playId = 0
    c.recientes.clear()
    sincronizar()
  }, [sincronizar])

  return {
    actual: estado.actual,
    pendientes: estado.pendientes,
    omitidas: estado.omitidas,
    playId: estado.playId,
    encolar,
    alTerminar,
    limpiar,
  }
}
