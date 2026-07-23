import { useEffect, useRef } from 'react'

export default function Subtitulos({ items }) {
  const listRef = useRef(null)

  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight
    }
  }, [items])

  if (items.length === 0) {
    return (
      <div className="subtitulos subtitulos--vacio">
        Esperando transcripción...
      </div>
    )
  }

  return (
    <div className="subtitulos" ref={listRef}>
      {items.map((item, i) => (
        <div
          key={item.id ?? i}
          className={`subtitulo ${item.final ? 'subtitulo--final' : 'subtitulo--provisional'}`}
        >
          {item.texto}
        </div>
      ))}
    </div>
  )
}
