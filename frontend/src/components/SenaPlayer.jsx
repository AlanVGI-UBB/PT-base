const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export default function SenaPlayer({ senas }) {
  if (!senas || senas.length === 0) return null

  return (
    <div className="sena-grid">
      {senas.map((s, i) => (
        <div key={i} className="sena-item">
          <video
            src={`${API_URL}${s.video_url}`}
            autoPlay
            muted
            loop
            className="sena-video"
          />
          <span className="sena-label">{s.texto_visible}</span>
        </div>
      ))}
    </div>
  )
}
