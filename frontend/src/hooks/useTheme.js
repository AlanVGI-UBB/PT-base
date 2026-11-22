import { useCallback, useEffect, useState } from 'react'

const THEME_KEY = 'puente_lsch_theme'

function leerTemaInicial() {
  try {
    const guardado = localStorage.getItem(THEME_KEY)
    if (guardado === 'dark' || guardado === 'light') return guardado
  } catch {
    // sin acceso a localStorage
  }
  return 'light'
}

export function useTheme() {
  const [theme, setTheme] = useState(leerTemaInicial)

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    const meta = document.querySelector('meta[name="theme-color"]')
    if (meta) {
      meta.setAttribute('content', theme === 'dark' ? '#121316' : '#F7F5F0')
    }
    try {
      localStorage.setItem(THEME_KEY, theme)
    } catch {
      // ignorar si el almacenamiento está restringido
    }
  }, [theme])

  const toggleTheme = useCallback(() => {
    setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'))
  }, [])

  return { theme, toggleTheme }
}
