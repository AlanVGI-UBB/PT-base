# SPEC-001 — Fundación del proyecto (scaffold + hello world WebSocket)

**Etapa del plan:** Semestre 1 · Etapa 1 (mes 1) — *Setup + estado del arte + contacto con comunidad sorda*
**Estado:** Completada — verificado end-to-end
**Depende de:** — (spec inicial)

---

## 1. Objetivo

Establecer la estructura base del repositorio y un entorno de desarrollo reproducible para **Puente LSCh**, dejando operativo un "hola mundo" end-to-end (backend FastAPI con WebSocket de eco + frontend PWA React/Vite) que valide que el stack funciona en conjunto antes de añadir complejidad funcional.

## 2. Contexto y supuestos

- El proyecto se documenta en `docs/README.md` y `docs/plan_desarrollo_tecnico.md`; esta spec ejecuta la Etapa 1 del plan.
- Stack fijado en el plan:
  - **Backend:** Python 3.11 + FastAPI (WebSockets nativos).
  - **Frontend:** PWA React + Vite (`vite-plugin-pwa`).
  - **Orquestación local:** Docker Compose.
  - **BD:** SQLite (no se usa en esta spec, solo se reserva el directorio).
- Entorno de desarrollo esperado: Windows 10/11 con PowerShell 5.1 (puede usarse WSL2 o Docker Desktop; se omite `source venv/bin/activate` y se usan rutas Windows `venv\Scripts\activate`).
- No se integra todavía ASR, Motor de matching, glosario ni MediaPipe. Esos se cubren en specs posteriores (mapeo sugerido al final).
- No se configura todavía CI/CD ni publicación de imágenes a registro.

## 3. Alcance

### Incluido
- Creación de la estructura de carpetas definida en el plan (sección 2).
- Backend FastAPI mínimo: endpoint `GET /health` + WebSocket `/ws/echo` que devuelve el texto recibido.
- Frontend PWA React + Vite mínimo: una vista que se conecta al WebSocket y muestra los mensajes eco recibidos, con manifest y service worker habilitados por `vite-plugin-pwa`.
- `docker-compose.yml` con dos servicios (`backend`, `frontend`) que levantan el sistema completo.
- Archivos de configuración base: `.gitignore`, `README.md` raíz, `backend/requirements.txt`, `backend/.env.example`, `frontend/package.json`, `AGENTS.md` con instrucciones de lint/typecheck/test.
- Documentación mínima de ejecución local (en `README.md` raíz) para los tres modos: backend aislado, frontend aislado y Docker Compose.

### Explícitamente fuera
- Integración de Google Cloud Speech-to-Text o Web Speech API (→ SPEC-002 PoC de transcripción).
- Motor de coincidencia texto→seña y modelo de datos del glosario (→ SPEC-003 glosario).
- Banco de videos de señas, captura de audio del profesor, vista profesor real, MediaPipe (→ specs posteriores).
- Logging de métricas, evaluación WER/SUS, autenticación, despliegue a la nube.

## 4. Requisitos

1. **R1 — Estructura de carpetas:** el repo contiene `backend/`, `backend/app/`, `backend/data/`, `frontend/`, `frontend/src/`, `ml/`, `docs/`, `specs/` tal cual se describe en el plan (sección 2), más `docker-compose.yml` y `README.md` en la raíz.
2. **R2 — Backend ejecutable en local:**
   - `backend/requirements.txt` con `fastapi`, `uvicorn[standard]` (y herramientas de desarrollo mencionadas en R7).
   - `backend/app/main.py` define la app FastAPI con:
     - `GET /health` → `{ "status": "ok" }`.
     - `WebSocket /ws/echo` → acepta texto y devuelve `{ "type": "echo", "text": "<recibido>", "received_at": "<iso8601>", "echoed_at": "<iso8601>" }`.
   - `backend/.env.example` documenta variables (`PORT=8000`).
   - Se puede iniciar con `uvicorn app.main:app --reload --port 8000` desde `backend/`.
3. **R3 — Frontend PWA ejecutable en local:**
   - `frontend/package.json` con `react`, `react-dom`, `vite`, `@vitejs/plugin-react`, `vite-plugin-pwa`. Usa **pnpm** como gestor de paquetes (`packageManager` declarado en `package.json`).
   - `frontend/src/main.jsx` monta la app.
   - `frontend/src/App.jsx` ofrece:
     - Un input de texto + botón "Enviar".
     - Un panel que muestra los mensajes eco recibidos por el WebSocket.
     - La URL del WebSocket se obtiene de `import.meta.env.VITE_WS_URL` (por defecto `ws://localhost:8000/ws/echo`).
   - `vite-plugin-pwa` activo (manifest con `name: "Puente LSCh"`, `display: standalone`), service worker generado en build.
   - `pnpm dev` inicia Vite en `http://localhost:5173`.
   - `pnpm build` genera build de producción sin errores.
4. **R4 — Docker Compose completo:**
   - `docker-compose.yml` define servicios `backend` ( imagen basada en `python:3.11-slim`, expone `8000`) y `frontend` (imagen basada en `node:20-alpine` con build de Vite servido por `nginx` u opcionalmente modo dev, expone `5173`).
   - `docker compose up --build` levanta ambos servicios y la PWA queda accesible en `http://localhost:5173` hablando con el backend en `http://localhost:8000`.
5. **R5 — Conexión end-to-end demostrada:** desde el frontend corriendo (local o Docker) se envía un texto y el panel muestra el eco correcto con timestamps.
6. **R6 — `.gitignore`** ignora `__pycache__/`, `venv/`, `.env`, `node_modules/`, `dist/`, `*.db`, `backend/data/videos_senas/`.
7. **R7 — `AGENTS.md`** en la raíz documenta:
   - Cómo ejecutar backend, frontend y compose.
   - Comando de lint/typecheck/test a usar (`ruff check backend`, `pnpm --prefix frontend build` como verificación mínima) para que futuras sesiones automatizadas lo respeten.
   - Gestor de paquetes JS: **pnpm** (no npm/yarn).
8. **R8 — `README.md` raíz** con descripción breve del proyecto, links a `docs/` y `specs/`, los tres modos de ejecución, y nota explícita de que el frontend usa `pnpm`.
9. **R9 — Sin dependencias externas a servicios pagados:** el sistema base se ejecuta sin credenciales de Google Cloud; cualquier integración de pago queda para specs posteriores.

## 5. Diseño técnico

### 5.1 Estructura de archivos final tras esta spec

```
proyecto-titulo/
├── AGENTS.md
├── README.md
├── .gitignore
├── docker-compose.yml
├── backend/
│   ├── .env.example
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── __init__.py
│   │   └── main.py
│   └── data/
│       └── .gitkeep
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   ├── public/
│   │   └── icon.svg
│   └── src/
│       ├── main.jsx
│       ├── App.jsx
│       └── App.css
├── ml/
│   └── .gitkeep
├── docs/           # ya existe
└── specs/          # ya existe
```

> Los submódulos `app/asr/`, `app/glossary/`, `app/signs_recognition/`, `app/evaluation/` y `app/evaluation/` **no** se crean vacíos en esta spec; se introducirán en sus specs correspondientes para mantener el árbol limpio.

### 5.2 Backend — `backend/app/main.py`

```python
from datetime import datetime, timezone
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app = FastAPI(title="Puente LSCh API", version="0.1.0")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.websocket("/ws/echo")
async def ws_echo(ws: WebSocket) -> None:
    await ws.accept()
    try:
        while True:
            payload = await ws.receive_text()
            await ws.send_json(
                {
                    "type": "echo",
                    "text": payload,
                    "received_at": datetime.now(timezone.utc).isoformat(),
                    "echoed_at": datetime.now(timezone.utc).isoformat(),
                }
            )
    except WebSocketDisconnect:
        return
```

### 5.3 Backend — `backend/requirements.txt`

```
fastapi==0.111.*
uvicorn[standard]==0.30.*
ruff==0.5.*
```

### 5.4 Frontend — `frontend/src/App.jsx` (resumen de comportamiento)

- Estado: `messages` (array), `input` (string), `socket` (ref).
- `useEffect`: abre `WebSocket(VITE_WS_URL)`, push en `messages` al llegar mensaje.
- Render: input controlado, botón "Enviar" que hace `socket.send(input)`, lista de mensajes.

### 5.5 Docker Compose

- `backend`: build `./backend`, puerto `8000`, comando `uvicorn app.main:app --host 0.0.0.0 --port 8000`.
- `frontend`: build `./frontend` (build Vite con `pnpm` + servidor estático nginx), puerto `5173`.
- `VITE_WS_URL` inyectado en tiempo de build apuntando a `ws://localhost:8000/ws/echo`.

## 6. Criterios de aceptación

- [ ] R1–R9 satisfechos.
- [ ] `cd backend && uvicorn app.main:app --reload` responde `GET /health` con 200.
- [ ] `cd frontend && pnpm install && pnpm dev` abre la PWA sin errores en consola.
- [ ] Al enviar un texto desde la PWA se ve el eco con timestamps ISO-8601.
- [ ] `docker compose up --build` deja el sistema usable en red local sin pasos manuales extra.
- [ ] `pnpm --prefix frontend build` finaliza sin warnings.
   - [ ] `ruff check backend` finaliza sin errores.

## 7. Tareas de implementación

1. Crear `.gitignore`, `README.md` y `AGENTS.md` en la raíz.
2. Crear estructura de carpetas (`backend/app`, `backend/data`, `frontend/src`, `frontend/public`, `ml/`).
3. Implementar backend (`main.py`, `requirements.txt`, `.env.example`, `Dockerfile`).
4. Implementar frontend (`package.json`, `vite.config.js`, `index.html`, `src/main.jsx`, `src/App.jsx`, `src/App.css`, `public/icon.svg`, `Dockerfile` con build Vite + nginx).
5. Escribir `docker-compose.yml`.
6. Verificar-backend-local: levantar y probar `/health` y `/ws/echo` (con `wscat` o el propio frontend).
7. Verificar-frontend-local: `pnpm install && pnpm dev`, mandar texto, ver eco.
8. Verificar-compose: `docker compose up --build` y repetir la prueba end-to-end.
9. Ejecutar `ruff check backend` y `pnpm --prefix frontend build` y dejar todo limpio.

## 8. Verificación

```powershell
# Backend
cd backend; python -m venv venv; .\venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
# otra terminal:
Invoke-RestMethod http://localhost:8000/health

# Frontend (ventra aparte)
cd frontend; pnpm install; pnpm dev
# abrir http://localhost:5173, enviar texto, ver eco

# Docker Compose (otra terminal)
docker compose up --build
# repetir la prueba desde un navegador

# Lint / build
ruff check backend
pnpm --prefix frontend build
```

## 9. Notas / decisiones diferidas

- **Python venv en Windows:** se congela `python -m venv venv` + `venv\Scripts\activate` en lugar de `source venv/bin/activate`. Documentarlo así en `README.md` y `AGENTS.md`.
- **Servidor estático del frontend en Docker:** se elige `nginx:alpine` para servir el build. Si genera fricción con el service worker de la PWA, cambiar a `vite preview` como fallback.
- **CI/CD:** fuera de alcance; se introducirá en una spec de calidad separada cuando el sistema base funcione.
- **`AGENTS.md`** es instrucción para sesiones automatizadas (opencode y similares); no reemplaza al `README.md`.

### Especificaciones siguientes (propuesta, no vinculantes todavía)
- SPEC-002 — PoC de transcripción profesor→alumno (Web Speech API + matching por substring, 10–15 términos).
- SPEC-003 — Modelo de datos del glosario y motor de coincidencia con spaCy.
- SPEC-004 — Migración a Google Cloud Speech-to-Text v2 streaming.
- SPEC-005 — PWA completa: vista alumno y vista profesor.
- SPEC-006 — Piloto de evaluación (WER, latencia, SUS).
- SPEC-007 (condicional) — Módulo secundario alumno→profesor (MediaPipe + DTW/k-NN).