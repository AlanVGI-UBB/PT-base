const LABELS = {
  conectado: 'Conectado',
  desconectado: 'Desconectado',
  reconectando: 'Reconectando...',
  fallo: 'Sin conexión',
}

export default function EstadoConexion({ estado, intentos = 0 }) {
  return (
    <span className={`estado-conexion estado-conexion--${estado}`} role="status">
      <span className="estado-conexion__dot" />
      {LABELS[estado] ?? estado}
      {estado === 'reconectando' && intentos > 0 ? ` (intento ${intentos}/5)` : ''}
    </span>
  )
}
