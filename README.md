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

- Python 3.11+ (probado con 3.11 y 3.14 con `faster-whisper`)
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

Para transcripción real en local con `faster-whisper` (en GPU CUDA si está disponible, o CPU en caso contrario):

```powershell
$env:ASR_PROVIDER = "whisper"
$env:WHISPER_MODEL = "small"
$env:WHISPER_DEVICE = "auto"
uvicorn app.main:app --port 8000
```

Si solo levantas el frontend en Docker y quieres apuntar nginx a este backend nativo con GPU, define `BACKEND_UPSTREAM=host.docker.internal:8000` (por defecto `backend:8000`).

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

## Verificación rápida (lint + build + tests)

```powershell
ruff check backend ml
pytest backend/tests
pytest ml/tests
pnpm --prefix frontend build
```

## Mediciones de la PoC (`ml/` y `docs/resultados_poc.md`)

Las dependencias de medición están separadas en `ml/requirements.txt` (`jiwer`, `psutil`, `websockets`) para no engrosar la imagen del backend:

```powershell
pip install -r ml\requirements.txt
python ml\evaluar_matching.py --datos ml\datos\frases_anotadas.jsonl --particion prueba
python ml\evaluar_asr.py --audio ml\datos\audio\clase_01_cerca.wav --referencia ml\datos\referencias\clase_01.txt --modelo small --device cuda --prompt-glosario
# Carga contra backend nativo en otra terminal con ASR_PROVIDER=stub:
python ml\prueba_carga.py --escenario A --minutos 5
```

Resultados consolidados, trazabilidad y limitaciones en [`docs/resultados_poc.md`](docs/resultados_poc.md).

## Glosario piloto provisional y clips de ensayo

El curso piloto (`INF-221 — Estructuras de Datos`), sus 15 conceptos y los archivos MP4 en `backend/data/videos_senas/` son una **propuesta provisional del autor para la Prueba de Concepto (PoC)**, sin acuerdo con PIESDI ni con un docente de la asignatura. Los videos son tarjetas de ensayo generadas automáticamente con `backend/scripts/generar_clips_ensayo.py` (sin personas ni configuración manual) y no constituyen señas validadas en LSCh.

Para regenerar los clips o resembrar la base local:

```powershell
cd backend
.\venv\Scripts\activate
python scripts\generar_clips_ensayo.py
python scripts\seed_glosario.py
```
