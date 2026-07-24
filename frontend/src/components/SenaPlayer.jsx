const API_BASE = import.meta.env.VITE_API_URL
const API_URL = API_BASE !== undefined ? API_BASE : 'http://localhost:8000'

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
