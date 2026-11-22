import ThemeToggle from './ThemeToggle'

function getInitials(nombre = '', apellido = '') {
  const n = (nombre || '').trim()
  const a = (apellido || '').trim()
  if (n && a) return `${n[0]}${a[0]}`.toUpperCase()
  if (n) return n.slice(0, 2).toUpperCase()
  return '?'
}

function formatRut(rut) {
  if (!rut) return ''
  const clean = rut.replace(/[.-]/g, '')
  if (clean.length < 2) return rut
  const dv = clean.slice(-1)
  const num = clean.slice(0, -1)
  return `${Number(num).toLocaleString('es-CL')}-${dv}`
}

export default function Header({ activeTab = 'home', user, onLogout, theme, onToggleTheme }) {
  return (
    <header className="header">
      <div className="header__inner">
        <button
          type="button"
          className="header__brand"
          onClick={() => { window.location.hash = '#/dashboard' }}
        >
          <span className="header__title">Puente LSCh</span>
        </button>

        <nav className="header__nav" aria-label="Navegación principal">
          <button
            type="button"
            className={`header__tab ${activeTab === 'home' ? 'header__tab--active' : ''}`}
            aria-current={activeTab === 'home' ? 'page' : undefined}
            onClick={() => { window.location.hash = '#/dashboard' }}
          >
            Inicio
          </button>
          <button
            type="button"
            className={`header__tab ${activeTab === 'history' ? 'header__tab--active' : ''}`}
            aria-current={activeTab === 'history' ? 'page' : undefined}
            onClick={() => { window.location.hash = '#/historial' }}
          >
            Historial
          </button>
        </nav>

        <div className="header__user">
          {onToggleTheme && <ThemeToggle theme={theme} onToggle={onToggleTheme} />}
          {user && (
            <div className="header__pill" title={`${user.nombre} ${user.apellido}`}>
              <span className="header__pill-name">{user.nombre} {user.apellido}</span>
              <span className="header__pill-sep" aria-hidden="true">·</span>
              <span className="header__pill-rut">{formatRut(user.rut)}</span>
            </div>
          )}
          {onLogout && (
            <button type="button" className="header__logout" onClick={onLogout} title="Cerrar sesión">
              Salir
            </button>
          )}
          <div className="header__avatar" title={user ? `${user.nombre} ${user.apellido}` : ''}>
            {user ? getInitials(user.nombre, user.apellido) : '?'}
          </div>
        </div>
      </div>
    </header>
  )
}
