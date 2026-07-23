import { useCallback, useEffect, useState } from 'react'

const STORAGE_KEY = 'puente_lsch_auth'

export function useAuth() {
  const [user, setUser] = useState(null)
  const [token, setToken] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored) {
      try {
        const data = JSON.parse(stored)
        setToken(data.token)
        setUser(data.user)
      } catch {
        localStorage.removeItem(STORAGE_KEY)
      }
    }
    setLoading(false)
  }, [])

  const login = useCallback((rut, nombre, apellido, token) => {
    const userData = { rut, nombre, apellido, token }
    setUser({ rut, nombre, apellido })
    setToken(token)
    localStorage.setItem(STORAGE_KEY, JSON.stringify(userData))
  }, [])

  const logout = useCallback(() => {
    setUser(null)
    setToken(null)
    localStorage.removeItem(STORAGE_KEY)
  }, [])

  return { user, token, loading, login, logout }
}
