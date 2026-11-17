# Puente LSCh

Plataforma de apoyo a la inclusión de estudiantes sordos en aula mediante Lengua de Señas Chilena (LSCh). Proyecto de Título — Ingeniería Civil en Informática.

> Documentación completa del proyecto en [`docs/`](docs/README.md). Plan de desarrollo técnico en [`docs/plan_desarrollo_tecnico.md`](docs/plan_desarrollo_tecnico.md). Especificaciones técnicas en [`specs/`](specs/README.md).

## Estado

🚧 En desarrollo — Etapa 1 (fundación del repositorio). Ver [`specs/SPEC-001-fundacion-proyecto.md`](specs/SPEC-001-fundacion-proyecto.md).

## Stack

- **Backend:** Python 3.11 + FastAPI (WebSockets). Lint: `ruff`.
- **Frontend:** PWA React + Vite. **Gestor de paquetes: `pnpm`** (no npm/yarn).
- **Orquestación local:** Docker Compose.

## Requisitos previos

- Python 3.11+ (probado con 3.11; cualquier 3.11/3.12/3.13 funciona para desarrollo)
- Node.js 20+ y **pnpm** (`npm i -g pnpm` o vía corepack)
- Docker y Docker Compose (opcional, para despliegue)

## Modos de ejecución

### 1) Backend aislado

```powershell
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Health: `http://localhost:8000/health`
WebSocket de eco: `ws://localhost:8000/ws/echo`

### 2) Frontend aislado (pnpm)

```powershell
cd frontend
pnpm install
pnpm dev
```

PWA disponible en `http://localhost:5173`. Por defecto se conecta a `ws://localhost:8000/ws/echo`; sobrescribe con un archivo `.env.local`:

```
VITE_WS_URL=ws://otro-host:8000/ws/echo
```

### 3) Docker Compose (ambos servicios)

```powershell
docker compose up --build
```

- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`

### 4) Cloudflare Tunnel

Para publicar la PWA mediante un túnel remoto de Cloudflare:

1. Revoca cualquier token que haya sido escrito directamente en `docker-compose.yml` y genera uno nuevo desde Cloudflare Zero Trust.
2. Crea un archivo `.env` en la raíz del proyecto (está ignorado por Git):

```dotenv
CLOUDFLARE_TUNNEL_TOKEN=pega_aqui_el_token_nuevo
```

3. En la ruta de aplicación publicada del túnel, configura el origen como
   `http://frontend:80`. `localhost` no funciona dentro del contenedor de
   `cloudflared`.
4. Ejecuta:

```powershell
.\run-cloudflare.ps1
```

Cloudflare termina HTTPS públicamente y la PWA usa automáticamente `wss://`
para el WebSocket. La URL pública es la configurada en la ruta del túnel.

## Verificación rápida (lint + build)

```powershell
ruff check backend
pnpm --prefix frontend build
```
