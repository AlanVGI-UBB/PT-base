import { useEffect, useRef, useState } from 'react'

export default function Landing() {
  return (
    <main className="landing">
      <div className="landing__logo">
        <svg width="64" height="64" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
          <rect width="64" height="64" rx="14" fill="#1f6feb"/>
          <path d="M20 14h6v36h-6zM34 14h6v36h-6z" fill="#fff"/>
          <path d="M14 26h36M14 38h36" stroke="#0d1117" strokeWidth="3" strokeLinecap="round"/>
        </svg>
        <h1>Puente LSCh</h1>
      </div>
      <p className="landing__sub">Plataforma de apoyo a la inclusión de estudiantes sordos mediante Lengua de Señas Chilena.</p>
      <div className="landing__botones">
        <button
          className="btn btn--profesor"
          onClick={() => window.location.hash = '#/profesor'}
        >
          Soy profesor
        </button>
        <button
          className="btn btn--alumno"
          onClick={() => window.location.hash = '#/alumno'}
        >
          Soy alumno
        </button>
      </div>
    </main>
  )
}
