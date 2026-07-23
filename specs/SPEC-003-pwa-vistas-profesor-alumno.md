# SPEC-003 — PWA: vistas profesor y alumno + captura de audio + reproducción de señas

**Etapa del plan:** Semestre 2 · Etapa 5 (interfaz del alumno + integración) integrada con Etapa 4 (captura de audio del profesor).
**Estado:** Completada — verificado end-to-end
**Depende de:** SPEC-001 (fundación PWA React+Vite), SPEC-002 (backend con `/ws/profesor`, `/ws/alumno/{curso_id}`, endpoints REST)

---

## 1. Objetivo

Construir la PWA completa del proyecto **Puente LSCh** con dos vistas reales:

1. **Vista profesor** — captura audio del micrófono con `getUserMedia` + `MediaRecorder`, lo envía por WebSocket al backend (`/ws/profesor?curso_id=...`) para su transcripción, y muestra un indicador de estado (grabando / detenido / error).
2. **Vista alumno** — se conecta al WebSocket `/ws/alumno/{curso_id}`, recibe eventos `{segmento, senas}` en tiempo real, muestra subtítulos en vivo y reproduce el video de la seña cuando hay coincidencia con el glosario.

La app reemplaza el demo de eco de SPEC-001 con una arquitectura de routing (rol profesor / rol alumno), selección de curso, y modo de desarrollo con stub (sin micrófono necesario para probar el flujo end-to-end).

## 2. Contexto y supuestos

- **Stack heredado:** React 18 + Vite 5 + `vite-plugin-pwa`, `pnpm`.
- **Backend de SPEC-002 ya implementado:**
  - `GET /api/cursos` — lista de cursos.
  - `GET /api/cursos/{id}/glosario` — términos del curso.
  - `WebSocket /ws/profesor?curso_id=...` — recibe audio binario (WebM/Opus) o texto; ejecuta ASR + matching; emite eventos a la sala.
  - `WebSocket /ws/alumno/{curso_id}` — recibe eventos broadcast de la sala.
  - `GET /data/videos_senas/{archivo}` — sirve clips MP4.
- **ASR_PROVIDER=stub** por defecto: el backend genera frases automáticas sin necesidad de audio real. Esto permite probar el flujo completo (subtítulos + señas) sin micrófono. Con `ASR_PROVIDER=google`, el audio del profesor se transcribe de verdad.
- El alumno puede estar en otro dispositivo (table, celular) — la PWA es responsive.
- No se implementa StillAlive/reconexión con backoff todavía; reconexión simple al desconectarse.

## 3. Alcance

### Incluido
- **Routing** entre vista profesor y alumno (sin React Router; selección de rol en landing + `?rol=profesor|alumno` en URL, o hash routing).
- **Vista profesor:**
  - Selección de curso (dropdown desde `GET /api/cursos`).
  - Botón "Iniciar transcripción" / "Detener" que controla `getUserMedia` + `MediaRecorder`.
  - Captura de audio en chunks de ~250ms (WebM/Opus), enviados como binario por `/ws/profesor?curso_id=...`.
  - Indicador visual de estado: conectando / grabando / detenido / error (permisos de micrófono denegados, etc.).
  - Muestra la transcripción en vivo (feedback al profesor de lo que está reconociendo el sistema) — el backend no envía eventos al profesor, así que la vista profesor muestra una confirmación de envío + contador de chunks enviados.
- **Vista alumno:**
  - Selección de curso (dropdown desde `GET /api/cursos`).
  - Conexión automática a `/ws/alumno/{curso_id}` al seleccionar curso.
  - Panel de subtítulos en vivo: cada evento `segmento` muestra el `texto`. Los segmentos `final=true` se consolidan; los `final=false` se muestran como texto provisional que se actualiza.
  - Panel de señas: cuando `senas` no está vacío, reproduce el video de cada seña (`senas[i].video_url`) en un panel lateral o superpuesto. Auto-play, loop opcional, control de volumen muteado (la seña es visual).
  - Indicador de estado de conexión (conectado / desconectado / reconectando).
  - Responsive: funciona en celular, tablet y laptop.
- **Landing page** inicial con dos botones grandes: "Soy profesor" / "Soy alumno" → redirige a la vista correspondiente.
- **PWA mejorada:** manifest actualizado, service worker para offline (caché de assets), instalable en móvil.
- **Hook `useWebSocket`** reutilizable para manejar conexión, reconexión simple, y eventos.
- **Configuración de URLs:** `VITE_API_URL` (REST) y `VITE_WS_URL` (WebSocket base), con defaults a `http://localhost:8000` y `ws://localhost:8000`.

### Explícitamente fuera
- Cálculo en vivo de WER, latencia reportada por UI, cuestionario SUS (→ SPEC-004).
- Módulo secundario alumno→profesor (MediaPipe, DTW) — fuera de scope.
- Autenticación/autorización de usuarios.
- Vista de administración del glosario (CRUD de términos desde la PWA) — se gestiona vía scripts/seed.
- Grabación del banco de señas completo (eso es tarea del autor fuera de la app).
- Modo offline completo (los subtítulos en vivo requieren conexión al backend en tiempo real).

## 4. Requisitos

1. **R1 — Landing page:** la ruta `/` muestra dos botones: "Soy profesor" → `/#/profesor`, "Soy alumno" → `/#/alumno`.
2. **R2 — Routing por hash:** `#/profesor` y `#/alumno` renderizan las vistas correspondientes sin librerías externas (state + `window.location.hash`).
3. **R3 — Vista profesor:**
   - Dropdown de cursos cargado desde `GET /api/cursos`.
   - Botón "Iniciar transcripción" que pide permisos de micrófono (`getUserMedia({ audio: true })`), crea `MediaRecorder` con mimeType `audio/webm;codecs=opus`, y empieza a enviar chunks binarios por WebSocket cada `timeslice=250ms`.
   - Botón "Detener" que para `MediaRecorder` y cierra el WebSocket del profesor.
   - Estados: `idle` → `conectando` → `grabando` → `detenido`; manejo de error si `getUserMedia` es denegado.
   - Muestra: curso seleccionado, estado actual, contador de chunks enviados, tiempo transcurrido.
4. **R4 — Vista alumno:**
   - Dropdown de cursos cargado desde `GET /api/cursos`.
   - Al seleccionar curso, se conecta a `/ws/alumno/{curso_id}` automáticamente.
   - Panel de subtítulos: lista de segmentos `final=true` consolidados + segmento `final=false` actual como texto provisional en gris.
   - Panel de señas: cuando un segmento tiene `senas` no vacío, reproduce el video (`senas[i].video_url`) en `<video autoPlay muted loop>`. Si hay múltiples señas, se reproducen en secuencia o en grid.
   - Estado de conexión (conectado / desconectado / reconectando) con indicador visual.
   - Responsive: subtítulos ocupan el ancho completo; el panel de señas se redimensiona o se superpone en móvil.
5. **R5 — Hook `useWebSocket(url, { onMessage, onOpen, onClose })`:** maneja conexión, reconexión simple (1 intento cada 3s), cierre limpio al desmontar.
6. **R6 — Configuración de URLs:** `VITE_API_URL` (default `http://localhost:8000`), `VITE_WS_URL` (default `ws://localhost:8000`). Ambas se sobrescriben en el build de Docker con `ARG`.
7. **R7 — PWA:** manifest actualizado con iconos (al menos el SVG existente), `display: standalone`, `theme_color`. Service worker activo para caché de assets estáticos.
8. **R8 — Estilo:** tema oscuro consistente con SPEC-001 (CSS variables), tipografía legible, subtítulos con tamaño de fuente ajustable por el alumno (botones A+ / A-).
9. **R9 — Funciona con stub:** con `ASR_PROVIDER=stub` en el backend, la vista alumno recibe frases automáticas cada ~1.5s y reproduce los videos de las señas correspondientes — sin necesidad de que el profesor active el micrófono.
10. **R10 — Funciona con audio real:** con `ASR_PROVIDER=google`, la vista profesor captura audio real y el alumno recibe la transcripción + señas.
11. **R11 — Build de producción:** `pnpm build` finaliza sin errores ni warnings. `pnpm preview` sirve el build.
12. **R12 — Docker Compose:** el frontend en Docker se construye con `VITE_WS_URL=ws://localhost:8000` y `VITE_API_URL=http://localhost:8000`, y la PWA queda accesible en `http://localhost:5173`.

## 5. Diseño técnico

### 5.1 Estructura de archivos

```
frontend/
├── package.json
├── vite.config.js
├── index.html
├── .env.local          # opcional, para dev local
├── public/
│   └── icon.svg
├── src/
│   ├── main.jsx        # punto de entrada (sin cambios)
│   ├── App.jsx         # router por hash + landing
│   ├── App.css
│   ├── hooks/
│   │   └── useWebSocket.js
│   ├── api/
│   │   └── cliente.js  # fetch helper para REST
│   ├── views/
│   │   ├── Landing.jsx
│   │   ├── ProfesorView.jsx
│   │   └── AlumnoView.jsx
│   └── components/
│       ├── CursoSelector.jsx     # dropdown reutilizable
│       ├── Subtitulos.jsx        # panel de subtítulos
│       ├── SenaPlayer.jsx        # reproductor de video de seña
│       └── EstadoConexion.jsx    # indicador visual
```

### 5.2 Routing por hash (`App.jsx`)

```jsx
const [hash, setHash] = useState(window.location.hash)
useEffect(() => {
  const handler = () => setHash(window.location.hash)
  window.addEventListener('hashchange', handler)
  return () => window.removeEventListener('hashchange', handler)
}, [])

if (hash === '#/profesor') return <ProfesorView />
if (hash === '#/alumno') return <AlumnoView />
return <Landing />
```

### 5.3 Hook `useWebSocket`

```jsx
export function useWebSocket(url, { onMessage, onOpen, onClose } = {}) {
  const wsRef = useRef(null)
  const [estado, setEstado] = useState('desconectado')
  const reconnectRef = useRef(null)

  const conectar = useCallback(() => {
    const ws = new WebSocket(url)
    wsRef.current = ws
    ws.onopen = () => { setEstado('conectado'); onOpen?.() }
    ws.onmessage = (e) => onMessage?.(JSON.parse(e.data))
    ws.onclose = () => {
      setEstado('desconectado'); onClose?.()
      reconnectRef.current = setTimeout(conectar, 3000)
    }
    return () => { ws.close(); clearTimeout(reconnectRef.current) }
  }, [url])

  useEffect(() => { conectar(); return () => wsRef.current?.close() }, [conectar])

  return { ws: wsRef, estado, send: (data) => wsRef.current?.send(data) }
}
```

### 5.4 Vista profesor — captura de audio

```jsx
const iniciarCaptura = async () => {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
  const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' })
  recorder.ondataavailable = (e) => {
    if (e.data.size > 0) ws.send(e.data)  // binario al backend
  }
  recorder.start(250)  // chunks cada 250ms
}
```

### 5.5 Vista alumno — render de eventos

```jsx
// estado:
// subtítulos: [{id, texto, final}]
// señas activas: [{lema, texto_visible, video_url}]

ws.onmessage = (evento) => {
  if (evento.type === 'segmento') {
    if (evento.final) {
      setSubtitulos(prev => [...prev, {id: evento.segment_id, texto: evento.texto, final: true}])
      if (evento.senas.length > 0) setSenasActivas(evento.senas)
    } else {
      // actualizar texto provisional
      setSubtitulos(prev => {
        const last = prev[prev.length - 1]
        if (last && !last.final) {
          return [...prev.slice(0, -1), {...last, texto: evento.texto}]
        }
        return [...prev, {id: evento.segment_id, texto: evento.texto, final: false}]
      })
    }
  }
}
```

### 5.6 Componente `SenaPlayer`

```jsx
function SenaPlayer({ senas }) {
  if (!senas || senas.length === 0) return null
  return (
    <div className="sena-grid">
      {senas.map((s, i) => (
        <video
          key={i}
          src={s.video_url}
          autoPlay
          muted
          loop
          className="sena-video"
        />
      ))}
    </div>
  )
}
```

### 5.7 Configuración de URLs

```
# frontend/.env.local (desarrollo)
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

```js
const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
const WS_URL = import.meta.env.VITE_WS_URL ?? 'ws://localhost:8000'
```

### 5.8 Docker Compose (cambio en args)

```yaml
frontend:
  build:
    args:
      VITE_WS_URL: ws://localhost:8000
      VITE_API_URL: http://localhost:8000
```

## 6. Criterios de aceptación

- [ ] R1–R12 satisfechos.
- [ ] Landing muestra botones "Soy profesor" / "Soy alumno".
- [ ] Vista profesor: dropdown de cursos, botón iniciar/detener, indicador de estado, contador de chunks.
- [ ] Vista alumno: dropdown de cursos, subtítulos en vivo, panel de señas, indicador de conexión.
- [ ] Con `ASR_PROVIDER=stub`: alumno recibe frases automáticas y ve videos de señas (sin micrófono).
- [ ] Con `ASR_PROVIDER=google` (si credenciales): profesor captura audio real y alumno recibe transcripción.
- [ ] Responsive en celular, tablet y laptop (DevTools device emulation).
- [ ] `pnpm build` sin warnings.
- [ ] `docker compose up --build` levanta todo y la PWA funciona end-to-end con stub.
- [ ] `ruff check backend` y `pytest backend/tests` siguen pasando (no se toca el backend).

## 7. Tareas de implementación

1. Crear estructura de carpetas (`hooks/`, `api/`, `views/`, `components/`).
2. Implementar `useWebSocket` (conexión, reconexión, send, estado).
3. Implementar `api/cliente.js` (fetch helper para REST).
4. Implementar `App.jsx` con routing por hash + Landing.
5. Implementar `CursoSelector` (dropdown reutilizable).
6. Implementar `ProfesorView` (getUserMedia + MediaRecorder + WebSocket binario + estados).
7. Implementar `AlumnoView` (WebSocket + subtítulos + señas).
8. Implementar `Subtitulos`, `SenaPlayer`, `EstadoConexion`.
9. Implementar control de tamaño de fuente (A+ / A-).
10. Actualizar `vite.config.js` (env vars, manifest).
11. Actualizar `Dockerfile` del frontend (args `VITE_API_URL`).
12. Actualizar `docker-compose.yml` (args del frontend).
13. Verificar build (`pnpm build`), dev (`pnpm dev`), Docker (`docker compose up --build`).
14. Verificar stub end-to-end (alumno recibe frases + ve videos).
15. Actualizar `docs/historial_implementacion.md` al commitear.

## 8. Verificación

```powershell
# Desarrollo local
cd frontend
pnpm install
pnpm dev
# abrir http://localhost:5173, ir a "Soy alumno", seleccionar curso
# en otra pestaña http://localhost:5173#/profesor, seleccionar curso, iniciar
# (con stub: no hace falta iniciar profesor, el alumno recibe frases solo)
# verificar: subtítulos aparecen, videos de señas se reproducen

# Build de producción
pnpm build
pnpm preview

# Docker Compose (backend + frontend)
docker compose up --build
# abrir http://localhost:5173, mismo flujo anterior

# Verificar que backend sigue OK
ruff check backend
pytest backend/tests
```

## 9. Notas / decisiones diferidas

- **Routing:** se usa hash routing manual sin React Router para mantener el bundle mínimo y evitar dependencias. Si la app crece, se puede migrar a React Router en una spec posterior.
- **Reconexión WebSocket:** simple (1 intento cada 3s). No se implementa backoff exponencial ni lógica de "stale connection" todavía.
- **Tamaño de fuente:** control A+ / A- persistido en localStorage. No se implementa tema claro/oscuro toggle (solo oscuro por ahora).
- **Captura de audio:** `MediaRecorder` con `audio/webm;codecs=opus` funciona en Chromium. Si el navegador no soporta ese mimeType, caer a default y registrar warning en consola.
- **Video de señas:** los placeholders MP4 actuales son archivos mínimos sin contenido real de video. Se reproducirá un frame negro o nada, pero el flujo (load → play → loop) queda verificado. Cuando el autor grabe los videos reales, solo se reemplazan los archivos en `backend/data/videos_senas/`.
- **Feedback al profesor:** el backend no envía confirmación al profesor de lo que transcribió. Si se quiere feedback en tiempo real en la vista profesor, se puede añadir un segundo WebSocket o un campo de respuesta en el futuro.
- **PWA offline:** el service worker cachea assets estáticos (JS, CSS, iconos). Los subtítulos en vivo requieren conexión activa al backend, así que "offline" solo aplica a la shell de la app, no a la funcionalidad en tiempo real.

### Spec siguiente (propuesta)
- SPEC-004 — Piloto de evaluación: cálculo de WER (jiwer) sobre transcripción persistida en SQLite, latencia end-to-end reportada, cuestionario SUS.