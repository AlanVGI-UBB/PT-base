# Historial de implementación por commit

Este archivo lleva un registro narrativo de lo que se implementa en cada commit del
proyecto **Puente LSCh**. Es un complemento del `git log`: acá se explica **qué se hizo
y por qué**, no solo qué archivos cambiaron.

## Convención

Cada entrada debe incluir:

- **Encabezado** con fecha ISO (`YYYY-MM-DD`), hash corto del commit (si ya se conoce)
  y referencia a la speccubierta (si aplica).
- **Resumen** de 1–2 frases del objetivo del commit.
- **Cambios** concretos (archivos o módulos nuevos/modificados, comportamiento
  añadido).
- **Verificación** ejecutada para darlo por bueno (comandos o comprobaciones).
- **Notas** opcionales (decisiones diferidas, seguimientos).

Regla: **antes de cada `git commit`** se debe agregar (o actualizar) la entrada
correspondiente en este archivo. Esto aplica a sesiones automatizadas (opencode y
similares) y a commits manuales.

---

## 2026-07-22 — `5aeee70` — Implementación inicial · scaffold + hello world WebSocket
**Refs:** SPEC-001 `specs/SPEC-001-fundacion-proyecto.md` (Completada)

**Resumen:** Se levantó la fundación del repositorio: estructura de carpetas del
proyecto, backend FastAPI mínimo con WebSocket de eco, frontend PWA React+Vite
gestionado con `pnpm`, y orquestación con Docker Compose.

**Cambios:**
- Raíz: `.gitignore`, `README.md`, `AGENTS.md`, `docker-compose.yml`.
- Backend (`backend/`):
  - `app/main.py` — FastAPI con `GET /health` y `WebSocket /ws/echo`
    (eco con timestamps ISO-8601).
  - `requirements.txt` (`fastapi`, `uvicorn[standard]`, `ruff`).
  - `.env.example`, `Dockerfile` (python:3.11-slim), `.dockerignore`, `data/.gitkeep`.
- Frontend (`frontend/`):
  - `package.json` con `packageManager: pnpm@9`, `vite.config.js` con
    `vite-plugin-pwa` (manifest + service worker), `index.html`.
  - `src/main.jsx`, `src/App.jsx` (input + panel de eco vía WebSocket),
    `src/App.css`, `public/icon.svg`.
  - `Dockerfile` (build Vite + nginx estático, con `ARG VITE_WS_URL`).
  - `.dockerignore`.
- `ml/.gitkeep` para reservar directorio de scripts de experimentación.
- `specs/SPEC-001-fundacion-proyecto.md` + `specs/README.md` (flujo de trabajo
  a base de specs).

**Verificación:**
- `ruff check backend` → `All checks passed!`
- `pnpm install` + `pnpm build` en `frontend/` → build OK, PWA generada
  (sw.js + manifest.webmanifest).
- Backend en local: `GET /health` → `{"status":"ok"}`.
- WebSocket `/ws/echo` → eco correcto con `received_at` / `echoed_at`.
- (Pendiente de ejecutar por el usuario) `docker compose up --build`.

**Notas:**
- Gestor de paquetes JS fijado a **pnpm** (no npm/yarn).
- No se incluyeron submódulos vacíos (`asr/`, `glossary/`, etc.) — se
  introducirán en sus specs correspondientes.
- Próxima spec prevista: SPEC-002 (backend completo del flujo profesor→alumno).

## 2026-07-22 — `7d17881` — Registro de hash en historial
**Refs:** docs/historial_implementacion.md

**Resumen:** Commit mínimo para sincronizar el hash `5aeee70` en el historial de
implementación, cumpliendo la regla de AGENTS.md.

**Cambios:**
- `docs/historial_implementacion.md` — hash añadido al encabezado de la entrada
  SPEC-001.

**Verificación:** n/a (commit documental).

---

## 2026-07-22 — `72d0c35` — Backend completo del flujo profesor→alumno
**Refs:** SPEC-002 `specs/SPEC-002-backend-flujo-profesor-alumno.md` (Completada)

**Resumen:** Se implementó el backend completo del núcleo profesor→alumno:
arquitectura modular con ASR streaming (capa abstracta con Google v2 + stub),
glosario SQLite, motor de coincidencia por lema con spaCy, WebSockets de
profesor/alumno con broadcast por sala, y logging mínimo de segmentos para
evaluación futura.

**Cambios:**
- **Nuevos submódulos** en `backend/app/`:
  - `core/config.py` — settings con pydantic-settings (`.env`).
  - `core/nlp.py` — singleton de spaCy (`es_core_news_md`).
  - `core/db.py` — conexión SQLite + init schema.
  - `asr/base.py` — interfaz `StreamingASRProvider` + `ResultadoASR` + factory.
  - `asr/stub.py` — `StubAsrProvider` (sin credenciales, frases prefijadas).
  - `asr/google_streaming.py` — `GoogleStreamingProvider` (v2 streaming, es-CL).
  - `glossary/schema.py` — gestión de esquema SQLite.
  - `glossary/repository.py` — CRUD curso/termino + seed idempotente.
  - `glossary/matching.py` — `buscar_terminos()` con lematización spaCy + n-gramas,
    filtrando stopwords (DET, ADP, CCONJ, SCONJ).
  - `evaluation/logging.py` — persistir sesiones y segmentos en SQLite.
  - `signs_recognition/__init__.py` — placeholder (módulo secundario, fuera de spec).
- **Endpoints** en `backend/app/main.py`:
  - `GET /health` (mantenido de SPEC-001).
  - `GET /api/cursos` — lista de cursos sembrados.
  - `GET /api/cursos/{id}/glosario` — términos del curso.
  - `POST /api/sesiones` — crear sesión de clase.
  - `WebSocket /ws/profesor?curso_id=...` — recibe audio/texto, ejecuta ASR +
    matching, emite eventos `{segmento, senas}` a la sala.
  - `WebSocket /ws/alumno/{curso_id}` — se une a sala, recibe eventos broadcast.
  - `WebSocket /ws/echo` (mantenido de SPEC-001).
  - `StaticFiles /data/videos_senas` — sirve clips MP4 de señas.
- **Esquema SQLite** (`data/schema.sql`): `curso`, `termino`, `sesion`, `segmento`.
- **Seed** (`scripts/seed_glosario.py` + `data/seed_glosario.json`): 1 curso piloto
  con 12 términos (lemas ajustados a spaCy real), 12 placeholders MP4.
- **Tests** (`backend/tests/`):
  - `test_schema.py` — creación, idempotencia, FK de esquema SQLite.
  - `test_matching.py` — n-grama largo, varios matches, flexiones verbales, sin match.
- **Actualizaciones:**
  - `requirements.txt` — `spacy>=3.8`, `pydantic-settings`, `pytest`, `pytest-asyncio`,
    `google-cloud-speech`.
  - `Dockerfile` — descarga `es_core_news_md`, ejecuta seed al arrancar.
  - `.env.example` — variables nuevas (`ASR_PROVIDER`, `SPACY_MODEL`, `DB_PATH`, etc.).
  - `AGENTS.md` — comando `pytest backend/tests` añadido a verificación mínima.
  - `specs/README.md` — SPEC-002 marcada como Completada.
  - `specs/SPEC-002-backend-flujo-profesor-alumno.md` — estado actualizado.

**Verificación:**
- `ruff check backend` → `All checks passed!`
- `pytest backend/tests` → 10/10 passed (matching + schema).
- Smoke end-to-end con `ASR_PROVIDER=stub`:
  - `GET /health` → `{"status":"ok"}`
  - `GET /api/cursos` → 1 curso.
  - `GET /api/cursos/1/glosario` → 12 términos.
  - `POST /api/sesiones?curso_id=1` → `sesion_id=1`.

**Notas:**
- Los lemas del glosario se ajustaron a los lemas reales que spaCy `es_core_news_md`
  devuelve (e.g., "derivada" → lema "derivado", "raíz cuadrada" → "raíz cuadrado").
  Esto es un requisito para que el matching por lema funcione correctamente.
- El matching filtra stopwords (DET, ADP, CCONJ, SCONJ) antes de buscar n-gramas,
  para que "teorema del valor medio" coincida con el lema "teorema valor medio".
- `GoogleStreamingProvider` requiere credenciales de Google Cloud; sin ellas,
  usar `ASR_PROVIDER=stub` para desarrollo.
- El frontend de SPEC-001 sigue funcionando con el backend nuevo (mismo `/ws/echo`).
- Próxima spec prevista: SPEC-003 (PWA con vistas profesor/alumno + captura de
  audio + reproducción de video de señas).

## 2026-07-23 — `75132e3` — PWA completa: vistas profesor y alumno
**Refs:** SPEC-003 `specs/SPEC-003-pwa-vistas-profesor-alumno.md` (Completada)

**Resumen:** Se implementó la PWA completa del proyecto con dos vistas reales:
profesor (captura de audio con getUserMedia + MediaRecorder, envío de chunks
binarios por WebSocket) y alumno (recepción de subtítulos en tiempo real +
reproducción de videos de señas). Se reemplazó el demo de eco de SPEC-001 con
una arquitectura de routing por hash, selección de curso, y hook reutilizable
de WebSocket.

**Cambios:**
- **Nuevos archivos** en `frontend/src/`:
  - `hooks/useWebSocket.js` — hook reutilizable: conexión, reconexión simple,
    send, estado (conectado/desconectado).
  - `api/cliente.js` — fetch helper para endpoints REST (`fetchCursos`,
    `fetchGlosario`, `crearSesion`).
  - `views/Landing.jsx` — landing con botones "Soy profesor" / "Soy alumno".
  - `views/ProfesorView.jsx` — captura de audio con getUserMedia +
    MediaRecorder (WebM/Opus, chunks 250ms), envío binario por WebSocket,
    indicador de estado (idle/conectando/grabando/detenido), contador de
    chunks, tiempo transcurrido, manejo de errores de permisos.
  - `views/AlumnoView.jsx` — conexión a `/ws/alumno/{curso_id}`, panel de
    subtítulos en vivo (final consolidado + provisional), panel de señas
    (reproducción automática de videos), control de tamaño de fuente (A+/A-).
  - `components/CursoSelector.jsx` — dropdown reutilizable cargado desde
    `GET /api/cursos`.
  - `components/Subtitulos.jsx` — render de subtítulos con scroll automático,
    distinción final/provisional.
  - `components/SenaPlayer.jsx` — reproductor de video de señas (autoPlay,
    muted, loop) con label de texto visible.
  - `components/EstadoConexion.jsx` — indicador visual de estado WebSocket.
- **Archivos modificados:**
  - `App.jsx` — routing por hash (`#/profesor`, `#/alumno`, landing por defecto).
  - `App.css` — tema completo (landing, vistas, subtítulos, señas, responsive).
  - `vite.config.js` — limpieza (ya no usa VITE_WS_URL hardcodeado al echo).
  - `frontend/Dockerfile` — soporte para ARG `VITE_API_URL` además de
    `VITE_WS_URL`.
  - `docker-compose.yml` — args de frontend actualizados, `ASR_PROVIDER=stub`
    en backend.
  - `specs/README.md` — SPEC-003 marcada como Completada.
  - `specs/SPEC-003-pwa-vistas-profesor-alumno.md` — estado actualizado.

**Verificación:**
- `pnpm build` → build OK, PWA generada (sw.js, manifest, 39 módulos).
- `ruff check .` → All checks passed.
- `pytest backend/tests` → 10/10 passed (no se tocó backend).
- `docker compose up --build` → levanta backend + frontend correctamente.
- Stub end-to-end: alumno recibe frases automáticas del stub y ve videos de
  señas cuando hay coincidencia con el glosario.

**Notas:**
- El hook `useWebSocket` maneja `null` url (no conecta) — útil cuando no hay
  curso seleccionado.
- Los videos de señas son placeholders (archivos mínimos sin contenido real);
  se reproducen sin error pero no muestran video real — se reemplazan cuando
  el autor grabe los clips.
- La reconexión WebSocket es simple (1 intento cada 3s); no hay backoff
  exponencial todavía.
- Próxima spec prevista: SPEC-004 (piloto de evaluación: WER, latencia, SUS).

## 2026-07-23 — `d444cfc` — Perfil único centrado en el estudiante + sesiones en vivo con fan-out + historial con replay
**Refs:** SPEC-004 `specs/SPEC-004-perfil-estudiante-sesiones-fanout-historial.md` (Completada)

**Resumen:** Reestructuración mayor del sistema. Se eliminó el modelo "profesor →
alumno" y se migró a un perfil único centrado en el estudiante con autenticación
(RUT + contraseña, JWT), dashboard académico, gestión de salas pub/sub con fan-out,
y un sistema completo de historial con replay de clases.

**Cambios:**

- **Backend — Modelo de datos:**
  - `schema.sql` ampliado con tablas `usuario`, `inscripcion`, `clase`, `evento_clase`.
  - `curso` ahora incluye `cod_ramo` (ej. "INF-221").
  - Identificador de sala: `[COD_RAMO]-[SECCION]` (ej. `INF-221-SEC1`).

- **Backend — Auth (`app/auth/` + `app/core/auth.py`):**
  - `POST /api/auth/login` — login con RUT + password, devuelve JWT.
  - `GET /api/auth/usuario/me?rut=...` — datos del usuario + carga académica.
  - JWT firmado con HS256, expiración 1h. Hash de passwords con SHA-256 + salt.
  - Preparado para migrar a SSO/OAuth2 con Intranet institucional en el futuro.

- **Backend — Salas (`app/salas/manager.py`):**
  - `RoomManager` con `RoomState`: emitter_ws, listeners (set), timeline en memoria.
  - Patrón pub/sub (fan-out): el audio se procesa una sola vez, resultado broadcast.
  - `RoomManager.existe()`, `.crear()`, `.obtener()`, `.agregar_listener()`, `.broadcast()`, `.eliminar()`.
  - Soporte para pausa/reanudación implícita (cuando el emisor deja de enviar audio).
  - Finalización con persistencia automática del timeline.

- **Backend — Historial (`app/historial/`):**
  - `repository.py` — CRUD `clase`/`evento_clase`: crear, finalizar, guardar evento, listar, detalle.
  - `routes.py` — `GET /api/historial?rut=...`, `GET /api/historial/{clase_id}`, `GET /api/salas/{room_id}/estado`.

- **Backend — main.py refactor:**
  - `WebSocket /ws/sala/{room_id}?rol=emitter|listener&token=...` unificado.
  - Eliminados `/ws/profesor` y `/ws/alumno/{curso_id}` (reemplazados por `/ws/sala`).
  - `POST /api/sesiones` eliminado (creado implícito al iniciar sala).
  - `/api/cursos?rut=...` ahora devuelve asignaturas inscritas del estudiante.
  - CORS middleware añadido.

- **Backend — Seed y configuración:**
  - `seed_glosario.json` ampliado: 2 cursos con cod_ramo, 1 usuario, 3 inscripciones.
  - `seed_glosario.py` siembra usuarios e inscripciones (DELETE ALL + INSERT).
  - `requirements.txt` añade `PyJWT`, `httpx`.
  - `config.py` + `.env.example` añaden `JWT_SECRET`, `SALA_TIMEOUT_MS`, `AUTH_PROVIDER`.

- **Backend — Tests (21/21):**
  - `test_auth.py` — login válido, login inválido, usuario/me, cursos con rut, health.
  - `test_sala.py` — sala estado sin sala, listener sin sala.
  - `test_historial.py` — historial lista, detalle, no encontrado.
  - `test_schema.py` + `test_matching.py` — actualizados y mantenidos.

- **Frontend — Auth:**
  - `useAuth.js` — hook con login, logout, persistencia en localStorage.
  - `LoginView.jsx` — formulario RUT + contraseña, manejo de errores.

- **Frontend — Nueva estructura de vistas:**
  - `DashboardView.jsx` — lista de asignaturas inscritas con estado en vivo, botón Entrar.
  - `SalaView.jsx` — vista unificada emisor/listener.
    - Emisor: `getUserMedia` + `MediaRecorder` (chunks 250ms), pausar/reanudar/finalizar.
    - Listener: recibe subtítulos + señas en tiempo real.
    - Clase finalizada: notificación + link a historial.
  - `HistorialView.jsx` — lista de clases guardadas (asignatura, fecha, duración).
  - `ClaseDetailView.jsx` — dos modos:
    - Modo Apunte: transcripción completa como texto continuo con badges de señas.
    - Modo Replay: reproductor interactivo que simula la traducción en vivo con Play/Pausa/velocidad 1x-2x.
  - `ReplayPlayer.jsx` — reproductor de timeline con barra de progreso.
  - `ControlesEmisor.jsx` — iniciar/pausar/reanudar/finalizar.

- **Frontend — Eliminaciones:**
  - `Landing.jsx`, `ProfesorView.jsx`, `AlumnoView.jsx` removidos del routing.
  - `App.jsx` refactorizado con nuevas rutas (`#/login`, `#/dashboard`, `#/sala/{id}`, `#/historial`, `#/historial/{id}`).
  - `App.css` reescrito con estilos de login, dashboard, sala, historial, replay, responsive.

- **Frontend — API:**
  - `cliente.js` ampliado: `loginRequest`, `fetchCursosUsuario`, `fetchUsuario`, `fetchSalaEstado`, `fetchHistorial`, `fetchHistorialDetalle`.

**Verificación:**
- `ruff check .` → All checks passed.
- `pytest backend/tests` → 21/21 passed.
- `pnpm --prefix frontend build` → build OK (43 módulos, PWA generada).
- `docker compose up --build` → listo para verificar end-to-end con stub.

**Notas:**
- Cambio de paradigma: el profesor no interactúa con la plataforma. Todo lo gestiona el estudiante.
- El micrófono lavalier se conecta al dispositivo del estudiante; el transmisor se entrega al profesor.
- El timeline de la clase se guarda en SQLite (no audio/video). Replay funcional con controles.
- El sistema está preparado para SSO/OAuth2 con Intranet institucional (interfaz conceptual).
- Stakeholders: comunidad sorda, estudiantes, profesores (indirectamente a través del lavalier).
- Próxima spec prevista: SPEC-005 (piloto de evaluación si se retoma el plan original).

## 2026-07-23 — `8b6f79b` — Rediseño del Dashboard (UI)
**Refs:** Mejora visual (sin spec formal)

**Resumen:** Rediseño completo del Dashboard para coincidir con la UI objetivo:
navbar superior con logo + LSCh Inclusion + tabs Home/History + iconos mic/settings,
tarjeta de usuario con nombre/RUT/badge de micrófono y botón Historial, sección
destacada de "Clase Actual" con título grande y botón "Iniciar Transmisión",
grid de 3 columnas con "Todas mis Asignaturas".

**Cambios:**
- `frontend/src/components/Header.jsx` — **nuevo**: navbar sticky con logo SVG
  (azul), título "LSCh Inclusion", tabs Home/History (con underline azul en activo),
  iconos de micrófono y settings.
- `frontend/src/views/DashboardView.jsx` — rediseñado:
  - Tarjeta de usuario: nombre + RUT formateado + badge "Micrófono Conectado"
    (con punto verde) + botón "Historial de Clases" + botón "Salir".
  - Sección "CLASE ACTUAL" destacada con badge azul, título grande del ramo
    actual, sección y botón primario "Iniciar Transmisión de Clase" con icono
    de micrófono.
  - Sección "Todas mis Asignaturas" con grid de 3 columnas (responsive a
    2 en tablet, 1 en móvil), cada card con título, sección y botón "Iniciar"
    con icono de play.
- `frontend/src/App.css` — reescrito: variables CSS refinadas, header sticky,
  user-card, clase-actual (centrado, tipografía grande), grid de asignaturas
  con `grid-template-columns: repeat(3, 1fr)`, botones con sombras, hover
  states, badges con punto verde animado, responsive breakpoints.
- `backend/data/seed_glosario.json` — ampliado:
  - 4 cursos: INF-221 Estructuras de Datos, MAT-101 Álgebra Lineal,
    FIS-110 Física General, HUM-105 Ética Profesional.
  - Usuario de prueba sigue siendo Juan Pérez (RUT 12345678-9, password test123).
  - Inscrito en los 4 cursos (sección 1 INF-221, sección 3 MAT-101,
    sección 2 FIS-110, sección 1 HUM-105).
  - Glosario con 29 términos distribuidos entre los 4 cursos (comparten
    términos como "duda", "clase", "ejercicio" para que el matching funcione).

**Verificación:**
- `pnpm build` → build OK (44 módulos, CSS 8.38 KB, JS 161 KB).
- La primera asignatura inscrita (INF-221) aparece como "Clase Actual"
  destacada; las otras 3 aparecen en el grid inferior.

**Notas:**
- La lógica de "Clase Actual" es simple: muestra la primera asignatura
  inscrita. Si quieres otra lógica (por horario, por uso reciente, etc.),
  se puede refinar.
- El icono de micrófono en la navbar y el badge "Micrófono Conectado"
  son visuales; el estado real del micrófono se gestiona al iniciar la
  transmisión en la vista de Sala.

## 2026-07-23 — `9317fbb` — Rediseño de la Sala de traducción (UI)
**Refs:** Mejora visual (sin spec formal)

**Resumen:** Rediseño completo de la vista de Sala (traducción en vivo) para
coincidir con la UI objetivo: top bar con Salir/título/badge EN VIVO/settings,
panel izquierdo de subtítulos con control de tamaño A+/A− y términos del
glosario resaltados en bold, panel derecho con reproductor de video de seña
y tarjeta flotante "TRADUCIENDO CONCEPTO CLAVE", bottom bar con estado del
sistema y controles Pausar/Finalizar.

**Cambios:**
- `frontend/src/views/SalaView.jsx` — reescrito:
  - **Top bar:** botón Salir (izq), título centrado con `roomId` formateado
    (ej. "INF-221 — Estructuras de Datos"), badge "EN VIVO" con punto rojo
    pulsante, botón de settings (der).
  - **Layout 2 columnas:** subtítulos (35%) + video (65%).
  - **Panel de subtítulos:** header con icono + "Transcripción en Tiempo Real"
    + A+/A− para tamaño de fuente (12-32px). Subtítulos finales con
    **términos del glosario resaltados** (bold, fondo azul translúcido).
    Estado al pie: "Escuchando al profesor..." con icono de micrófono.
  - **Panel de video:** reproductor con aspect-ratio 16:9, gradiente oscuro,
    botones flotantes (expandir, más opciones) en esquina inferior derecha.
  - **Tarjeta concepto clave:** aparece flotante en esquina inferior izquierda
    cuando se detecta un término, mostrando "TRADUCIENDO CONCEPTO CLAVE" +
    término + icono de mano. Se oculta automáticamente tras 4s.
  - **Bottom bar (solo emisor):** "Estado del Sistema — Audio y video
    sincronizados" (izq) + botones "Pausar/Reanudar Transcripción" (gris
    oscuro) y "Finalizar y Guardar" (rojo con sombra).
- `frontend/src/App.css` — sección de Sala completamente nueva:
  - `.sala`, `.sala-topbar`, `.sala-grid` con grid 2 columnas.
  - `.sala-subtitulos__contenido` con scroll y tamaño de fuente dinámico.
  - `.sala-video__player` con gradiente y aspect-ratio.
  - `.concepto-card` con animación slideIn y backdrop-filter.
  - `.sala-bottombar` con `btn--ghost-pause` y `btn--detener-finalizar`.
  - `.termino` para highlight de glosario.
  - Animación `pulse` para el badge "EN VIVO".

**Verificación:**
- `pnpm build` → build OK (41 módulos, CSS 12.61 KB, JS 166 KB).

**Notas:**
- La función `highlightText` usa regex sobre los `texto_visible` de los
  términos matched para envolverlos en `<strong class="termino">`.
- El título de la sala se construye reemplazando el primer `-` por ` — `
  para mostrar "INF-221 — Estructuras de Datos".
- La tarjeta de concepto se muestra solo cuando hay match, con auto-hide
  tras 4s para no saturar la UI.
- El "EN VIVO" badge está siempre visible (la transmisión está activa
  mientras el emisor no finalice).