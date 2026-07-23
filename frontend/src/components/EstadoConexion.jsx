const LABELS = {
  conectado: 'Conectado',
  desconectado: 'Desconectado',
  reconectando: 'Reconectando...',
}

export default function EstadoConexion({ estado }) {
  return (
    <span className={`badge badge--${estado}`}>
      {LABELS[estado] ?? estado}
    </span>
  )
}
