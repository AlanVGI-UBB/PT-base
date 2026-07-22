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

## 2026-07-22 — Implementación inicial · scaffold + hello world WebSocket
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
- Próxima spec prevista: SPEC-002 (PoC de transcripción profesor→alumno con
  Web Speech API + matching por substring).