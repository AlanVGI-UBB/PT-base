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

## 2026-07-23 — <pendiente> — PWA completa: vistas profesor y alumno
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