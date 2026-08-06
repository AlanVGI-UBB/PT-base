function getInitials(nombre = '', apellido = '') {
  const n = (nombre || '').trim()
  const a = (apellido || '').trim()
  if (n && a) return `${n[0]}${a[0]}`.toUpperCase()
  if (n) return n.slice(0, 2).toUpperCase()
  return '?'
}

export default function Header({ activeTab = 'home', user }) {
  return (
    <header className="header">
      <div className="header__brand">
        <div className="header__logo">
          <svg width="36" height="36" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect width="64" height="64" rx="14" fill="#4a7eff"/>
            <path d="M20 14h6v36h-6zM34 14h6v36h-6z" fill="#fff"/>
            <path d="M14 26h36M14 38h36" stroke="#0d1117" strokeWidth="3" strokeLinecap="round"/>
          </svg>
        </div>
        <span className="header__title">Inclusión LSCh</span>
      </div>

      <nav className="header__nav">
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
        <div className="header__avatar" title={user ? `${user.nombre} ${user.apellido}` : ''}>
          {user ? getInitials(user.nombre, user.apellido) : '?'}
        </div>
      </div>
    </header>
  )
}
