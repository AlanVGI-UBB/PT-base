# SPEC-002 — Backend del flujo profesor→alumno (ASR + glosario + matching + logging mínimo)

**Etapa del plan:** Semestre 1 · Etapa 2+3+4 consolidadas + Semestre 2 · Etapa 4 (parcial). Sustituye el enfoque incremental PoC→MVP del plan por una implementación directa de la arquitectura final del núcleo.
**Estado:** Completada — verificado end-to-end
**Depende de:** SPEC-001 (fundación del repositorio: FastAPI, WebSockets, Docker Compose)

---

## 1. Objetivo

Construir el backend completo del flujo **profesor → alumno** tal como lo tendrá el sistema final: captura de audio del profesor por WebSocket, transcripción en streaming mediante una **capa abstracta `ASRProvider`** (por defecto Google Cloud Speech-to-Text v2, con respaldos definibles), coincidencia del texto transcrito contra el glosario del curso en SQLite usando **spaCy** (`es_core_news_md`), y emisión de eventos `{segmento, señas}` a los clientes alumno. Se incluye **instrumentación mínima** (sesiones, segmentos con timestamps, transcripción persistida) que deje el sistema listo para el piloto de evaluación (SPEC-004) sin reescribir el backend.

Esta spec no incluye la PWA ( vistas profesor/alumno) ni el cálculo en vivo de WER/SUS — esos van en SPEC-003 y SPEC-004 respectivamente. Tampoco incluye el módulo secundario alumno→profesor (MediaPipe/DTW), que queda fuera hasta que el núcleo esté sólido.

## 2. Contexto y supuestos

- **Decisión del autor (22/07/2026):** abandonar el incremento PoC del plan; construir la arquitectura final del núcleo de una vez, sin pasos intermedios de "juguete".
- **Stack heredado de SPEC-001:** Python 3.11 + FastAPI (WebSockets), Docker Compose.
- **Medios técnicos del plan:**
  - ASR: Google Cloud Speech-to-Text v2 (streaming, `es-CL`). Audio del profesor capturado con `MediaRecorder` en chunks ≈250ms, códec Opus/WebM.
  - Matching: spaCy `es_core_news_md` para lematización + diccionario por lema; n-gramas hasta 3.
  - Glosario: SQLite (80–150 términos para el piloto; aquí se define el esquema y se carga una muestra sembrada para probar).
  - Videos de señas: MP4 servidos como estáticos desde el backend.
- **Supuestos operativos:**
  - El backend puede no tener credenciales de Google Cloud durante el desarrollo → se provee una implementación `GoogleStreamingProvider` (default) **y** una `StubAsrProvider` que repite texto fijo/reproducido para avanzar sin credenciales. Las implementaciones `WebSpeechAsrProvider` (texto que llega desde el navegador) y `FasterWhisperProvider` (GPU local) se definen como variantes de la misma interfaz, pero su implementación completa se cubre en una spec posterior o dentro de esta solo si el tiempo lo permite — aquí se pide la interfaz y Google + Stub.
  - El modelo `es_core_news_md` de spaCy se descarga en build (cacheado en la imagen Docker).
  - El desarrollo ocurre en Windows 11 + PowerShell 5.1; el venv local ya existe (`backend/venv`).

## 3. Alcance

### Incluido
- **Arquitectura modular del backend** con submódulos: `app/asr/`, `app/glossary/`, `app/core/`, `app/evaluation/` (reservado `app/signs_recognition/` para el módulo secundario, fuera de esta spec).
- **Capa abstracta `ASRProvider`** (`StreamingASRProvider`) con:
  - `GoogleStreamingProvider` (default): reenvía el stream de audio a Google Cloud Speech-to-Text v2 y devuelve resultados parciales/finales.
  - `StubAsrProvider`: sin credenciales; reproduce frases prefijadas para permitir integración end-to-end durante el desarrollo.
  - Interfaz declarada para `WebSpeechAsrProvider` y `FasterWhisperProvider` (variantes futuras).
- **WebSocket de transcripción** `/ws/profesor`:
  - Recibe audio binario (WebM/Opus en chunks) o texto cuando el cliente use Web Speech API en el navegador.
  - Devuelve eventos `{ type, segment_id, texto, final, senas: [...] }` a todos los clientes **alumno** conectados a la misma sesión.
- **WebSocket de alumno** `/ws/alumno/{sala}`: se une a una sala (curso), recibe los eventos emitidos por la sala.
- **Endpoints REST:**
  - `GET /health` (mantenido de SPEC-001).
  - `GET /api/cursos` → lista de cursos.
  - `GET /api/cursos/{id}/glosario` → términos del curso (texto_visible, video_url).
  - `GET /data/videos_senas/{archivo}` → archivos estáticos de video.
  - `POST /api/sesiones` → crear sesión de clase (id, curso, timestamps).
- **Modelo de datos SQLite** (gestión con `sqlite3` estándar o `SQLModel` — ver §5.4) para `curso`, `termino`, `sesion`, `segmento` (con transcripción, timestamps y `video_match`).
- **Motor de coincidencia** `app/glossary/matching.py` con spaCy + n-gramas por lema.
- **Sembrado del glosario** con 10–15 términos de muestra (uno o dos cursos piloto) + 1–2 videos MP4 placeholder para que el flujo end-to-end sea verificable sin grabar todo el banco.
- **Logging estructurado** de cada segmento en SQLite para WER/latencia posterior (sin cálculo en vivo — va en SPEC-004).
- **Tests unitarios mínimos** del motor de coincidencia y del esquema SQLite (pytest), ya que SPEC-002 introduce lógica no trivial. Se actualiza `AGENTS.md` con el comando de test.
- **Configuración:** `.env` soporta `ASR_PROVIDER=google|stub|webspeech|faster_whisper`, `GOOGLE_APPLICATION_CREDENTIALS`, `SPACY_MODEL`, `PORT`, `DB_PATH`.
- **Docker:** `backend/Dockerfile` actualizado para instalar dependencias (spaCy, `google-cloud-speech`, `python-multipart` si hace falta) y descargar el modelo `es_core_news_md`.

### Explícitamente fuera
- PWA y vistas profesor/alumno (→ SPEC-003).
- Cálculo en vivo/automático de WER, latencia reportada por UI, cuestionario SUS (→ SPEC-004).
- Módulo secundario alumno→profesor: `app/signs_recognition/` y MediaPipe/DTW (→ spec posterior, condicional).
- Banco de señas completo (80–150 clips): se reservan `backend/data/videos_senas/` y se sembrarán 1–2 placeholders; la carga completa es una tarea del autor durante el piloto.
- Autenticación/autorización, multi-curso simultáneo en producción, despliegue a la nube.
- Capa de CI/CD (spec de calidad posterior).

## 4. Requisitos

1. **R1 — Estructura de módulos:** `backend/app/` contiene `core/`, `asr/`, `glossary/`, `evaluation/`. Cada submódulo expone su responsabilidad vía `__init__.py`. `main.py` queda como ensamblador de routers y WebSocket handlers.
2. **R2 — Interfaz `ASRProvider`** definida en `app/asr/base.py`. Toda implementación:
   - Expone `async transcribe_stream(audio_iter, lang="es-CL") -> AsyncIterator[ResultadoASR]` donde `ResultadoASR` tiene `texto`, `estable` (bool), `inicio`, `fin`.
   - Es instanciable desde una factory `get_asr_provider(provider: str | None)` que lee `ASR_PROVIDER` del env.
3. **R3 — `GoogleStreamingProvider`** implementado:
   - Usa `google-cloud-speech` v2 con streaming recognize, `es-CL`, config `Linear16` o `WebM/Opus` según chunks.
   - Maneja error de credenciales ausentes lanzando `AsrConfigError` con mensaje accionable.
4. **R4 — `StubAsrProvider`** implementado y usable sin credenciales:
   - Acepta `audio_iter` (ignorado) y devuelve un flujo de frases prefijadas (`["hola mundo", "derivada", "raíz cuadrada", "teorema del valor medio", ...]`) con temporización controlable (vía env `STUB_INTERVAL_MS`, default 1500).
5. **R5 — WebSocket `/ws/profesor`**:
   - Acepta conexión, lee mensajes binarios (audio) o texto.
   - Usa el `ASRProvider` configurado para generar resultados; para cada uno corre el matching contra el glosario de la sala/curso indicado en query params (`?curso_id=1`).
   - Emite a todos los alumnos de la sala un evento JSON:
     ```json
     { "type": "segmento", "segment_id": 123, "texto": "...", "final": false,
       "senas": [ {"lema": "derivada", "texto_visible": "derivada", "video_url": "/data/videos_senas/derivada.mp4"} ],
       "t": 1719... }
     ```
6. **R6 — WebSocket `/ws/alumno/{curso_id}`**:
   - Se une a la sala indicada; recibe todos los eventos emitidos para esa sala.
   - Mantiene un heartbeat/ping para detectar desconexiones.
7. **R7 — Glosario SQLite** con esquema (al menos):
   ```sql
   CREATE TABLE curso (id INTEGER PRIMARY KEY, nombre TEXT NOT NULL);
   CREATE TABLE termino (
     id INTEGER PRIMARY KEY,
     curso_id INTEGER REFERENCES curso(id),
     lema TEXT NOT NULL,
     texto_visible TEXT NOT NULL,
     video_url TEXT NOT NULL,
     n_palabras INTEGER DEFAULT 1
   );
   CREATE TABLE sesion (
     id INTEGER PRIMARY KEY,
     curso_id INTEGER REFERENCES curso(id),
     inicio TEXT NOT NULL,
     fin TEXT
   );
   CREATE TABLE segmento (
     id INTEGER PRIMARY KEY,
     sesion_id INTEGER REFERENCES sesion(id),
     texto TEXT,
     recibido_at TEXT,
     emitido_at TEXT,
     estable INTEGER DEFAULT 0,
     senas_json TEXT
   );
   ```
   Migración/esquema gestionado por un script `app/glossary/schema.py` o SQL en `backend/data/schema.sql`; la BD se crea al arranque si no existe.
8. **R8 — Motor de coincidencia** `app/glossary/matching.py`:
   - Carga el glosario del curso desde SQLite y mapea por lema.
   - `buscar_terminos(texto, glosario_por_lema, max_ngrama=3)` returns list de `Match` (lema, rango, término).
   - N-gramas largos primero para capturar "raíz cuadrada" antes de "raíz" y "cuadrada" por separado.
9. **R9 — spaCy** `es_core_news_md` descargado en el contenedor; cargado una sola vez al inicio (patrón singleton en `app/core/nlp.py`).
10. **R10 — Sembrado:** un script `backend/scripts/seed_glosario.py` (o migración equivalente) inserta 1–2 cursos piloto con 10–15 términos cada uno y registra 1–2 videos MP4 placeholder en `backend/data/videos_senas/`.
11. **R11 — Logging:** cada segmento recibido en `/ws/profesor` se persiste en `segmento` con `recibido_at` y `emitido_at` ISO-8601, `estable` (0/1) y `senas_json`. El `sesion_id` se crea explícitamente con `POST /api/sesiones` o implícitamente al primer segmento.
12. **R12 — Endpoints REST** mínimos (`GET /api/cursos`, `GET /api/cursos/{id}/glosario`, `POST /api/sesiones`, `GET /data/videos_senas/{archivo}`); documentados en `/docs` (OpenAPI automático de FastAPI).
13. **R13 — Tests:** `backend/tests/test_matching.py` cubre:
    - match nuevo con n-grama largo (`"raíz cuadrada"`).
    - match con variantes flexivas (`"hablando"` → `["hablar"]` si existe).
    - varios matches en un mismo texto.
    `backend/tests/test_schema.py` prueba creación + seed del SQLite. Suite ejecutable con `pytest`.
14. **R14 — Config y env:** `.env.example` documenta todas las variables nuevas; `.env` sigue en `.gitignore`.
15. **R15 — `WebSocket /ws/echo`** de SPEC-001 se conserva (para sanity / smoke tests).
16. **R16 — Verificación mínima:** `ruff check backend` y `pytest backend/tests` pasan; además `docker compose up --build` levanta backend y frontend de SPEC-001 sin romper.

## 5. Diseño técnico

### 5.1 Estructura de archivos

```
backend/
├── .env.example
├── Dockerfile
├── requirements.txt
├── app/
│   ├── __init__.py
│   ├── main.py                 # ensamblador: routers, ws handlers, startup
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py           # settings via pydantic-settings
│   │   ├── nlp.py              # spaCy singleton
│   │   └── db.py               # conexion sqlite + init schema
│   ├── asr/
│   │   ├── __init__.py
│   │   ├── base.py             # StreamingASRProvider + ResultadoASR + factory
│   │   ├── google_streaming.py
│   │   ├── stub.py
│   │   ├── web_speech.py       # solo doc/comentado; variante futura
│   │   └── faster_whisper.py   # solo doc/comentado; variante futura
│   ├── glossary/
│   │   ├── __init__.py
│   │   ├── repository.py       # CRUD termino/curso
│   │   ├── matching.py         # buscar_terminos()
│   │   └── schema.py           # CREATE TABLE + migracion simple
│   ├── evaluation/
│   │   ├── __init__.py
│   │   └── logging.py          # persist segmentos/sesiones (SQLite)
│   └── signs_recognition/       # fuera de esta spec - placeholder __init__ vacio si se crea
├── data/
│   ├── schema.sql
│   ├── glosario.db             # (gitignored)
│   ├── seed_glosario.json      # seed cursos/terminos
│   └── videos_senas/
│       ├── derivada.mp4        # placeholder
│       └── raiz_cuadrada.mp4   # placeholder
├── scripts/
│   └── seed_glosario.py        # carga seed_glosario.json en SQLite
└── tests/
    ├── test_matching.py
    └── test_schema.py
```

### 5.2 Flujo end-to-end (backend)

```
Profesor (navegador/PWA) ──WS binario──> /ws/profesor?curso_id=1
                                            │
                                            ▼
                          ASRProvider (google | stub | ...)
                                            │ stream ResultadoASR
                                            ▼
                          glossary.matching.buscar_terminos()
                                            │
                                            ▼
                          evaluation.logging.persist_segmento() ─► SQLite
                                            │
                                            ▼
                          broadcast {segmento, senas} a sala/curso 1
                                            │
                                            ▼
Alumno (navegador/PWA) ◄──WS── /ws/alumno/1
```

### 5.3 Interfaz `ASRProvider`

```python
# app/asr/base.py
from dataclasses import dataclass
from typing import AsyncIterator, Protocol

@dataclass
class ResultadoASR:
    texto: str
    estable: bool       # final vs parcial
    inicio_ms: int
    fin_ms: int

class StreamingASRProvider(Protocol):
    async def transcribe_stream(
        self,
        audio_iter: AsyncIterator[bytes],
        lang: str = "es-CL",
    ) -> AsyncIterator[ResultadoASR]: ...

def get_asr_provider(provider: str | None = None) -> StreamingASRProvider: ...
```

### 5.4 Persistencia

Se usa `sqlite3` estándar + un helper `app/core/db.py` que abre conexión por request (o un pool mínimo con `threading.local`). No se introduce un ORM completo salvo que la complejidad lo justifique; se prefiere **SQLModel** solo si el CRUD glosario crece. Decisión diferida a implementación; ver §9.

### 5.5 Coincidencia por lema

```python
# app/glossary/matching.py
from app.core.nlp import nlp

def buscar_terminos(texto, glosario_por_lema, max_ngrama=3):
    doc = nlp(texto)
    lemas = [t.lemma_.lower() for t in doc]
    encontrados = []
    i = 0
    while i < len(lemas):
        match = None
        for n in range(min(max_ngrama, len(lemas) - i), 0, -1):
            candidato = " ".join(lemas[i:i+n])
            if candidato in glosario_por_lema:
                match = glosario_por_lema[candidato]
                i += n
                break
        if match:
            encontrados.append(match)
        else:
            i += 1
    return encontrados
```

### 5.6 Configuración (`.env.example`)

```
PORT=8000
ASR_PROVIDER=stub            # google | stub | webspeech | faster_whisper
GOOGLE_APPLICATION_CREDENTIALS=
SPACY_MODEL=es_core_news_md
DB_PATH=data/glosario.db
STUB_INTERVAL_MS=1500
```

### 5.7 Dependencias nuevas (`requirements.txt`)

```
fastapi==0.111.*
uvicorn[standard]==0.30.*
ruff==0.5.*
spacy==3.7.*
# modelo descargado en Dockerfile y en documentación de setup local
google-cloud-speech==2.31.*
pydantic-settings==2.3.*
pytest==8.*
pytest-asyncio==0.23.*
```

### 5.8 Dockerfile (cambios clave)

```dockerfile
RUN pip install --upgrade pip && pip install -r requirements.txt
RUN python -m spacy download es_core_news_md
COPY app/ ./app/
COPY data/schema.sql ./data/
COPY scripts/ ./scripts/
# servidor de archivos estáticos para /data/videos_senas (via FastAPI StaticFiles)
```

## 6. Criterios de aceptación

- [ ] R1–R16 satisfechos.
- [ ] `GET /api/cursos` y `GET /api/cursos/{id}/glosario` devuelven datos sembrados correctamente.
- [ ] Con `ASR_PROVIDER=stub`, conectarse a `/ws/profesor?curso_id=1` no requiere audio real y los alumnos conectados a `/ws/alumno/1` reciben eventos `{segmento, senas}`.
- [ ] Con `ASR_PROVIDER=google` y credenciales válidas, el flujo produce transcripciones reales en `es-CL`. (Validado manualmente; sin credenciales en CI.)
- [ ] `buscar_terminos("vamos a ver la raíz cuadrada de un número")` retorna `["raíz cuadrada"]` (no por separado).
- [ ] `buscar_terminos("mientras él estaba hablando, derivó la función")` retorna `["hablar", "derivada"]` cuando ambos términos existen en el glosario (lemas).
- [ ] `pytest backend/tests` pasa; cobertura mínima de matching y schema.
- [ ] `ruff check backend` pasa.
- [ ] `docker compose up --build` levanta backend + frontend sin romper SPEC-001.
- [ ] Cada segmento procesado deja una fila en `segmento` con timestamps correctos.

## 7. Tareas de implementación

1. Crear submódulos `app/core/`, `app/asr/`, `app/glossary/`, `app/evaluation/`.
2. Implementar `core/config.py` (pydantic-settings) y `core/nlp.py` (spaCy singleton).
3. Implementar `glossary/schema.py` + `data/schema.sql`; crear BD al arranque.
4. Implementar `glossary/repository.py` para `curso`, `termino` (y opcional CRUD).
5. Implementar `glossary/matching.py` + tests.
6. Implementar `asr/base.py` (interfaz + factory) y `asr/stub.py`.
7. Implementar `asr/google_streaming.py` (v2 `es-CL`); manejar error de credenciales.
8. Implementar `evaluation/logging.py` (persist `sesion`, `segmento`).
9. Implementar en `main.py`:
   - `POST /api/sesiones`
   - `GET /api/cursos`, `GET /api/cursos/{id}/glosario`
   - `StaticFiles` en `/data/videos_senas`
   - `/ws/profesor?curso_id=...` y `/ws/alumno/{curso_id}`
10. Mantener `/health` y `/ws/echo` de SPEC-001.
11. Crear `scripts/seed_glosario.py` + `data/seed_glosario.json` + 2 placeholders MP4.
12. Actualizar `requirements.txt`, `Dockerfile`, `.env.example`.
13. Escribir `tests/test_matching.py` y `tests/test_schema.py`.
14. Verificar (`ruff`, `pytest`, smoke con stub, docker compose).
15. Actualizar `AGENTS.md` con el nuevo comando de tests (`pytest backend/tests`).
16. Actualizar `docs/historial_implementacion.md` al commitear.

## 8. Verificación

```powershell
cd backend
.\venv\Scripts\activate
pip install -r requirements.txt
python -m spacy download es_core_news_md
python scripts\seed_glosario.py
pytest backend/tests
ruff check backend
uvicorn app.main:app --reload --port 8000

# smoke stub:
# 1) connect /ws/alumno/1 y dejar escuchando
# 2) connect /ws/profesor?curso_id=1 con ASR_PROVIDER=stub
# 3) verificar eventos emitidos en ~1.5s intervalos
```

```powershell
docker compose up --build
# igual prueba anterior con stub, en red local
```

## 9. Notas / decisiones diferidas

- **ORM:** si `glossary/repository.py` crece, migrar a SQLModel. Por ahora `sqlite3` directo.
- **Multiplexión de salas:** usar un `dict[curso_id, set[WebSocket]]` en memoria (suficiente para el piloto). Para multi-instancia en producción sería necesario Redis pub/sub — fuera de scope.
- **Formato de audio:** `MediaRecorder` produce WebM/Opus en Chromium. Google v2 lo acepta con `codec: OGG_OPUS`; si la pista del navegador no encaja, transcoding a `Linear16` en backend - diferir a implementación si aparece el problema.
- **Web Speech como respaldo:** la variante `WebSpeechAsrProvider` sería en realidad un handler pasivo: el navegador ya transcribe y reenvía texto. Se modela por simetría con la interfaz aunque el streaming no viene de audio server-side.
- **`app/signs_recognition/`:** se deja fuera de esta spec; se introducirá en la spec del módulo secundario si el tiempo lo permite.
- **`AGENTS.md`:** tras implementar, completar el comando de tests en la sección de verificación mínima ("`pytest backend/tests`").

### Spec siguiente (propuesta)
- SPEC-003 — Frontend PWA: vistas profesor y alumno, captura de audio, render de subtítulos + reproducción del video de la seña. Integración con `/ws/profesor` y `/ws/alumno/{curso}`.
- SPEC-004 — Piloto de evaluación: cálculo de WER (jiwer) sobre transcripción persistida, latencia end-to-end reportada, cuestionario SUS.