# Puente LSCh

Plataforma web progresiva (PWA) de apoyo a la inclusión de estudiantes sordos en aula universitaria mediante subtítulos en tiempo real y apoyo visual terminológico en Lengua de Señas Chilena (LSCh). Proyecto de Título — Ingeniería Civil en Informática (Universidad del Bío-Bío).

> **Documentación del proyecto:**
> - Plan técnico: [`docs/plan_desarrollo_tecnico.md`](docs/plan_desarrollo_tecnico.md)
> - Especificaciones (`SPEC-001` a `SPEC-009`): [`specs/README.md`](specs/README.md)
> - Decisiones técnicas del prototipo: [`docs/decisiones_tecnicas.md`](docs/decisiones_tecnicas.md)
> - Resultados cuantitativos de la PoC: [`docs/resultados_poc.md`](docs/resultados_poc.md)
> - Guía técnica y de defensa: [`docs/documentacion_prototipo_defensa.md`](docs/documentacion_prototipo_defensa.md)
> - Historial de implementación por commit: [`docs/historial_implementacion.md`](docs/historial_implementacion.md)

## Estado

Prototipo de Prueba de Concepto (PoC) completado hasta **`SPEC-009`**:

- Autenticación por RUT con contraseñas derivadas (`scrypt`) y JWT de jornada (`480 min`).
- Autorización por inscripción en salas WebSocket, glosario, estado de sala, historial y clips protegidos (`/api/cursos/{curso_id}/senas/{termino_id}/video`).
- Permiso explícito de captura (`inscripcion.puede_capturar`) y aviso obligatorio de condiciones de registro antes de activar el micrófono.
- Transcripción real en local con captura PCM (`AudioWorklet` 16 kHz) y `faster-whisper` (GPU CUDA o CPU), más proveedor `stub` para desarrollo.
- Pausa y reanudación gestionadas en el servidor con aviso visible para oyentes, registro de discontinuidades (`pausa`, `reanudacion`, `desconexion`) y marca de `"Registro incompleto"` ante cierres por desconexión (`timeout`).
- Motor de coincidencia terminológica (`spaCy` doble clave + bloqueos + abstenciones), cola acotada de señas, historial en modo **Apunte** y **Replay** continuo.

## Stack

- **Backend:** Python 3.11+ (probado en 3.11 y 3.14), FastAPI, SQLite (WAL), `faster-whisper`, `spaCy` (`es_core_news_md`). Lint: `ruff`.
- **Frontend:** PWA React 18 + Vite 5. **Gestor de paquetes: `pnpm`** (no `npm` ni `yarn`).
- **Orquestación local:** Docker Compose (con Nginx TLS autofirmado) y soporte opcional para Cloudflare Tunnel.

## Requisitos previos

- Python 3.11+ y `pip`
- Node.js 20+ y **`pnpm`** (`corepack enable` o `npm i -g pnpm`)
- Docker y Docker Compose (opcional, para despliegue local con HTTPS o túnel)

## Modos de ejecución

### 1) Desarrollo nativo (recomendado para usar GPU CUDA en Windows)

**Backend:**

```powershell
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
python -m spacy download es_core_news_md
python scripts\seed_glosario.py
uvicorn app.main:app --reload --port 8000
```

Para transcripción real en local con `faster-whisper` (usa GPU CUDA si está disponible y cae a CPU en caso contrario):

```powershell
$env:ASR_PROVIDER = "whisper"
$env:WHISPER_MODEL = "small"
$env:WHISPER_DEVICE = "auto"
uvicorn app.main:app --port 8000
```

Verificación rápida: `http://localhost:8000/health`

**Frontend (en otra terminal):**

```powershell
cd frontend
pnpm install
pnpm dev
```

PWA disponible en `http://localhost:5173`. Si deseas apuntar el frontend a otro backend, crea `frontend/.env.local` con `VITE_API_URL` y `VITE_WS_URL`.

### 2) Docker Compose con HTTPS local

Para probar desde celulares o tablets en la misma red Wi-Fi (el navegador exige HTTPS para `getUserMedia` y `AudioWorklet`):

```powershell
.\run.ps1
```

O manualmente:

```powershell
docker compose up --build
```

- Nginx genera automáticamente una CA de desarrollo (`/ca.crt`) y certificado TLS para `CERT_HOST` (`localhost` o tu IPv4 local).
- Frontend HTTPS: `https://localhost` (o `https://<tu-ip>`).
- Backend API: `http://localhost:8000` (proxeado por Nginx bajo `/api/` y `/ws/` en el mismo origen).
- Si deseas usar el contenedor `frontend` contra un backend nativo con GPU, define `BACKEND_UPSTREAM=host.docker.internal:8000`.
- Define `JWT_SECRET` en un archivo `.env` en la raíz si quieres que las sesiones sobrevivan a reinicios del contenedor.

### 3) Cloudflare Tunnel (HTTPS/WSS público sin instalar certificados)

1. Crea un archivo `.env` en la raíz del repositorio (ignorado por Git):

```dotenv
CLOUDFLARE_TUNNEL_TOKEN=tu_token_de_cloudflare_zero_trust
JWT_SECRET=un_secreto_aleatorio_de_al_menos_32_caracteres
```

2. En Cloudflare Zero Trust, configura el origen de la ruta publicada como `http://frontend:80` (`localhost` no funciona dentro del contenedor `cloudflared`).
3. Ejecuta:

```powershell
.\run-cloudflare.ps1
```

Cloudflare termina HTTPS públicamente y la PWA usa `wss://` automáticamente.

## Usuarios de prueba (seed local)

Todos los usuarios sembrados por `backend/scripts/seed_glosario.py` tienen contraseña **`test123`** (almacenada con `hashlib.scrypt` y sal aleatoria por usuario):

| RUT | Nombre | Inscripciones | Rol esperado en pruebas |
|---|---|---|---|
| `12345678-5` | Juan Pérez | `INF-221` sec. `1` (`puede_capturar=1`), `MAT-101` sec. `3` (`puede_capturar=1`) | Emisor autorizado: puede iniciar transmisión y pausar/finalizar. |
| `9876543-3` | María González | `INF-221` sec. `1` (`puede_capturar=0`), `MAT-101` sec. `3` (`puede_capturar=0`) | Oyente: no ve botón de inicio; entra a una clase activa como oyente. |
| `11111111-1` | Pedro Soto | `MAT-101` sec. `3` (`puede_capturar=0`) | Prueba negativa (`CA01`): sin acceso a sala, glosario ni clips de `INF-221`. |

## Variables de entorno del backend

Lista completa en [`backend/.env.example`](backend/.env.example):

| Variable | Por defecto | Descripción |
|---|---|---|
| `PORT` | `8000` | Puerto de escucha del servidor FastAPI |
| `ASR_PROVIDER` | `stub` | Proveedor ASR: `stub` o `whisper` |
| `WHISPER_MODEL` | `small` | Modelo de `faster-whisper` (`tiny`, `base`, `small`, etc.) |
| `WHISPER_DEVICE` | `auto` | `auto` (CUDA si existe, si no CPU), `cuda` o `cpu` |
| `WHISPER_COMPUTE_TYPE` | `auto` | `auto` (`float16` en CUDA, `int8` en CPU) o tipo explícito |
| `ASR_SILENCIO_MS` | `600` | Silencio o ausencia de tramas (ms) que consolida un segmento |
| `ASR_MAX_SEGMENTO_MS` | `15000` | Duración máxima de un segmento continuo (ms) |
| `ASR_PARCIAL_MS` | `1000` | Cadencia mínima de resultados provisionales (ms) |
| `ASR_FLUSH_TIMEOUT_MS` | `5000` | Tiempo máximo de espera al vaciar el búfer al finalizar (ms) |
| `ASR_MAX_TRAMA_BYTES` | `64000` | Tamaño máximo de trama PCM aceptada por mensaje WebSocket |
| `ASR_PROMPT_GLOSARIO` | `true` | Inyecta el glosario activo como `initial_prompt` de Whisper |
| `SPACY_MODEL` | `es_core_news_md` | Modelo de `spaCy` para el índice y matching |
| `DB_PATH` | `data/glosario.db` | Ruta de la base de datos SQLite |
| `STUB_INTERVAL_MS` | `1500` | Intervalo entre frases en modo `stub` |
| `JWT_SECRET` | *(vacío)* | Secreto HS256 (≥ 32 bytes). Si queda vacío se genera uno aleatorio al arrancar (con advertencia en logs) |
| `JWT_EXP_MIN` | `480` | Vigencia del token en minutos (8 horas) |
| `CORS_ORIGINS` | `http://localhost:5173` | Orígenes permitidos separados por coma (`allow_credentials=False`) |
| `SALA_TIMEOUT_MS` | `30000` | Ventana antes de cerrar automáticamente tras desconexión del emisor |
| `METRICAS` | `true` | Activa el registro de latencias por segmento en `metrica_segmento` |

## Verificación rápida (lint + tests + build)

```powershell
ruff check backend ml
pytest backend/tests
pytest ml/tests
pnpm --prefix frontend build
```

## Mediciones de la PoC (`ml/` y `docs/resultados_poc.md`)

Las dependencias de evaluación están separadas en `ml/requirements.txt` (`jiwer`, `psutil`, `websockets`):

```powershell
pip install -r ml\requirements.txt
python ml\evaluar_matching.py --datos ml\datos\frases_anotadas.jsonl --particion prueba
python ml\evaluar_asr.py --audio ml\datos\audio\clase_01_cerca.wav --referencia ml\datos\referencias\clase_01.txt --modelo small --device cuda --prompt-glosario
# Carga contra backend nativo en otra terminal con ASR_PROVIDER=stub:
python ml\prueba_carga.py --escenario A --minutos 5
```

Resultados consolidados, trazabilidad y limitaciones en [`docs/resultados_poc.md`](docs/resultados_poc.md) y su explicación en lenguaje simple en [`docs/explicacion_pruebas_poc.md`](docs/explicacion_pruebas_poc.md).

## Recursos de ensayo y alcance provisional

- **Glosario piloto y clips:** el curso piloto (`INF-221 — Estructuras de Datos`), sus 15 conceptos y los 15 archivos MP4 en `backend/data/videos_senas/` son **provisionales para la PoC**, sin validación lingüística de intérpretes ni acuerdo con PIESDI. Los videos son tarjetas de texto generadas con `backend/scripts/generar_clips_ensayo.py` y se muestran rotulados en pantalla como *"Clip de ensayo · sin validación lingüística"*.
- **Aviso de condiciones de registro:** el texto del modal previo a la captura es provisional y no sustituye la autorización institucional ni la política definitiva que se acuerde con PIESDI.

Para regenerar los clips o resembrar la base local:

```powershell
cd backend
.\venv\Scripts\activate
python scripts\generar_clips_ensayo.py
python scripts\seed_glosario.py
```
