export default function ControlesEmisor({ estado, onIniciar, onPausar, onReanudar, onFinalizar, tiempo, chunks }) {
  const fmt = (s) => `${Math.floor(s / 60).toString().padStart(2, '0')}:${(s % 60).toString().padStart(2, '0')}`

  if (estado === 'idle') {
    return (
      <button className="btn btn--iniciar" onClick={onIniciar}>
        Iniciar transmisión
      </button>
    )
  }

  return (
    <div className="controles-emisor">
      <div className="controles-emisor__estado">
        <span className="badge badge--grabando">Transmitiendo</span>
        <span className="controles-emisor__tiempo">{fmt(tiempo)}</span>
        <span className="controles-emisor__chunks">{chunks} chunks</span>
      </div>
      <div className="controles-emisor__botones">
        {estado === 'grabando' ? (
          <button className="btn btn--fuente" onClick={onPausar}>Pausar</button>
        ) : (
          <button className="btn btn--fuente" onClick={onReanudar}>Reanudar</button>
        )}
        <button className="btn btn--detener" onClick={onFinalizar}>Finalizar y Guardar</button>
      </div>
    </div>
  )
}
