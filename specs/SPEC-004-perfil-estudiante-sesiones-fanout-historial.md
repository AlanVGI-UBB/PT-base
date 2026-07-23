# SPEC-004 — Perfil único centrado en el estudiante + sesiones en vivo con fan-out + historial con replay

**Etapa del plan:** Reestructuración mayor del sistema. Sustituye el modelo "profesor → alumno" de SPEC-002/SPEC-003 por un modelo centrado en el estudiante que captura el audio del profesor con un micrófono lavalier conectado al propio dispositivo del alumno. Introduce autenticación, dashboard académico, gestión de salas pub/sub, y historial con replay.
**Estado:** Completada — verificado end-to-end
**Depende de:** SPEC-001 (fundación), SPEC-002 (backend: ASR, glosario, matching, SQLite), SPEC-003 (PWA React+Vite, captura de audio, WebSockets)

---

## 1. Objetivo

Rediseñar el sistema alrededor de un **único perfil de usuario: el estudiante sordo**. El estudiante gestiona su propio dispositivo (PWA) y el micrófono lavalier inalámbrico conectado a él; el transmisor se entrega al profesor. El estudiante inicia una sesión de clase para su asignatura/sección, el sistema transcribe el audio una sola vez (ASR + matching), y el resultado se difunde en tiempo real a todos los compañeros de la misma sección conectados a la sala. Al finalizar, la clase queda guardada como un *timeline* JSON en SQLite para revisión asíncrona (modo lectura y modo replay).

## 2. Contexto y supuestos

- **Cambio de paradigma:** el sistema ya no tiene vista de profesor. El profesor no interactúa con la plataforma; solo usa el transmisor del lavalier. El estudiante es quien opera la app.
- **Hardware:** micrófono lavalier inalámbrico con receptor USB-C/Jack que se conecta al dispositivo del estudiante. El dispositivo reconoce el receptor como entrada de audio estándar — no se necesita configuración especial en la app.
- **Autenticación institucional:** conceptualmente el sistema se integrará con la Intranet de la universidad vía SSO/OAuth2. Para el prototipo/MVP se autentica localmente contra una tabla SQLite que simula la API de la Intranet (RUT + contraseña + carga académica).
- **Identificador de sala:** cada sección activa se identifica por el código único `[COD_RAMO]-[SECCION]` (ej. `INF-221-SEC1`). Dos secciones del mismo ramo son salas independientes y aisladas.
- **Eficiencia:** el audio de una clase se procesa **una sola vez** por el ASR y el motor de matching. El resultado se difunde (broadcast) a todos los clientes suscritos a la sala. No se duplican llamadas ASR por cada alumno conectado.
- **Stack heredado:** Python 3.11 + FastAPI (WebSockets), SQLite, spaCy, React + Vite PWA, Docker Compose.
- **No se guarda audio ni video** de la clase — solo el timeline de texto + IDs de señas.

## 3. Alcance

### Incluido

#### 3.1 Autenticación y perfil de usuario
- **Login** con RUT + contraseña (autenticación local contra SQLite para el MVP).
- Tabla `usuario` en SQLite con: `rut`, `password_hash`, `nombre`, `apellido`.
- Endpoint `POST /api/auth/login` que valida credenciales y devuelve un token (JWT simple o token opaco en memoria para el MVP).
- Middleware de autenticación que protege los endpoints de la API.
- **Carga académica:** tabla `inscripcion` que relaciona `usuario.rut` con `curso` (asignatura) + `seccion`. Al iniciar sesión, el sistema devuelve la lista de asignaturas activas del estudiante (código de ramo, nombre, sección).
- Esquema preparado conceptualmente para migrar a SSO/OAuth2 con la Intranet en el futuro (interfaz `AuthProvider` con implementación `LocalAuthProvider`).

#### 3.2 Dashboard del estudiante
- Vista principal tras login: lista de asignaturas inscritas (código, nombre, sección).
- Cada asignatura tiene un botón "Entrar a la clase".
- Indicador visual de si hay una transmisión activa para esa sección (punto verde "En vivo" / gris "Sin clase activa").

#### 3.3 Gestión de sesiones en vivo
- **Selección de asignatura/sección:** el estudiante selecciona la clase que está cursando.
- **Verificación de sala activa:** el backend verifica si ya existe una transmisión activa para `[COD_RAMO]-[SECCION]`.
  - **Escenario 1 (Sin transmisión previa):** el estudiante inicia la transmisión. Se crea la sala en el backend. El dispositivo del estudiante actúa como **emisor** de audio (captura con `getUserMedia` + `MediaRecorder`) **y** receptor de la traducción (subtítulos + señas). Controles: `[Pausar]`, `[Reanudar]`, `[Finalizar y Guardar]`.
  - **Escenario 2 (Transmisión existente):** si otro compañero ya inició la clase, el sistema notifica al estudiante y lo une automáticamente a la sala como **oyente/suscriptor** (`listener`). El alumno recibe los subtítulos y señas en tiempo real pero no captura audio. No se requiere hardware adicional ni se duplican llamadas ASR.
- **Secciones simultáneas:** dos clases del mismo ramo pero diferente sección son salas independientes y aisladas.

#### 3.4 Arquitectura pub/sub (fan-out)
- **Registro de salas en memoria:** `dict[room_id, RoomState]` donde `room_id = "[COD_RAMO]-[SECCION]"`.
- **RoomState** contiene: `emitter_ws` (el WebSocket del emisor), `listeners_ws` (set de WebSockets de oyentes), `asr_provider`, `glosario_por_lema`, `sesion_id`, `timeline` (lista de segmentos en memoria).
- **Procesamiento O(1):** el audio que llega del emisor se procesa una sola vez (ASR + matching). El resultado se difunde a **todos** los WebSockets de la sala (emisor + listeners).
- **WebSocket unificado** `/ws/sala/{room_id}?token=...`:
  - Query param `?rol=emitter|listener` para distinguir el rol (el backend determina el rol según si la sala ya existe o no).
  - El emisor envía audio binario; los listeners no envían datos (solo reciben).
  - Todos reciben los eventos `{segmento, senas}` en broadcast.
- **Control de pausa/reanudación:** el emisor puede pausar la captura (`MediaRecorder.pause()`) y reanudarla. El backend deja de recibir audio y por tanto de emitir segmentos. Al reanudar, el flujo continúa.
- **Finalizar y guardar:** el emisor presiona "Finalizar y Guardar" → el backend cierra la sala, persiste el timeline completo en SQLite, y notifica a todos los listeners que la clase terminó.

#### 3.5 Historial y reproducción asíncrona (replay)
- **Almacenamiento liviano (Timeline JSON):** al finalizar una clase, se guarda en SQLite un registro con:
  - `clase` table: `id`, `room_id`, `curso_id`, `rut_emisor`, `fecha_inicio`, `fecha_fin`, `duracion_ms`.
  - `evento_clase` table: `id`, `clase_id`, `timestamp_ms` (relativo al inicio de la clase), `texto`, `estable`, `senas_json` (lista de `{lema, texto_visible, video_url}`).
- **Endpoints REST de historial:**
  - `GET /api/historial?rut=...` → lista de clases guardadas del estudiante.
  - `GET /api/historial/{clase_id}` → timeline completo de una clase.
- **Vista de historial en la PWA:**
  - Lista de clases pasadas (asignatura, fecha, duración).
  - **Modo Apunte/Lectura:** despliegue de la transcripción completa como texto continuo para revisión rápida. Las señas se muestran como badges/nombres junto al texto (no se reproducen video).
  - **Modo Simulación (Replay):** reproductor interactivo que simula la traducción en vivo. Recorre el timeline según los `timestamp_ms`, muestra subtítulos progresivamente y reproduce los clips de señas sincronizados. Controles: `[Play]`, `[Pausa]`, barra de progreso, velocidad de reproducción (1x / 1.5x / 2x).

#### 3.6 Refactor del frontend
- Eliminación de las vistas `ProfesorView` y `Landing` (ya no hay rol profesor).
- Nuevas vistas: `LoginView`, `DashboardView`, `SalaView` (emisor/listener unificado), `HistorialView`, `ClaseDetailView` (apunte + replay).
- Routing por hash: `#/login`, `#/dashboard`, `#/sala/{room_id}`, `#/historial`, `#/historial/{clase_id}`.
- Persistencia del token de auth en `localStorage`.

#### 3.7 Refactor del backend
- **Rutas WebSocket:** reemplazar `/ws/profesor` y `/ws/alumno/{curso_id}` por `/ws/sala/{room_id}` unificado.
- **Endpoints REST nuevos:** `/api/auth/login`, `/api/usuario/me`, `/api/historial`, `/api/historial/{clase_id}`.
- **Endpoints REST modificados:** `/api/cursos` ahora devuelve las asignaturas inscritas del estudiante autenticado (no todos los cursos).
- **Middleware de auth:** protección de endpoints con token.
- **Modelo de datos SQLite ampliado:** `usuario`, `inscripcion`, `clase`, `evento_clase` (además de `curso`, `termino`, `sesion`, `segmento` existentes — `sesion`/`segmento` se mantienen para compatibilidad o se migran a `clase`/`evento_clase`).

### Explícitamente fuera
- Integración real con SSO/OAuth2 de la Intranet (solo se deja la arquitectura preparada).
- Grabación de audio/video de la clase (solo timeline JSON).
- Notificaciones push (email, etc.) al iniciar una clase.
- Chat entre estudiantes durante la clase.
- Exportación del timeline a PDF u otros formatos (puede añadirse en spec posterior).
- Módulo secundario alumno→profesor (MediaPipe/DTW) — sigue fuera de scope.
- Cálculo de WER/SUS/piloto de evaluación (→ SPEC-005 si se retoma el plan de evaluación).
- Panel de administración del glosario desde la PWA (se sigue gestionando via scripts/seed).
- Rate limiting o control de concurrencia de salas a escala de producción (suficiente para piloto universitario).

## 4. Requisitos

1. **R1 — Autenticación local:**
   - Tabla `usuario` (`rut` TEXT PK, `password_hash` TEXT, `nombre` TEXT, `apellido` TEXT).
   - Tabla `inscripcion` (`rut` TEXT FK→usuario, `curso_id` INTEGER FK→curso, `seccion` TEXT, PRIMARY KEY (`rut`, `curso_id`, `seccion`)).
   - `POST /api/auth/login` recibe `{rut, password}`, valida contra `password_hash` (bcrypt o sha256+salt para simplicidad del MVP), devuelve `{token, rut, nombre, apellido}`.
   - `GET /api/usuario/me` (con token) devuelve los datos del usuario + carga académica (lista de `{curso_id, cod_ramo, nombre, seccion}`).
   - Middleware que valida token en endpoints protegidos.
   - Seed de al menos 1 usuario de prueba con 2-3 inscripciones.

2. **R2 — Dashboard:**
   - Tras login, la PWA muestra `DashboardView` con la lista de asignaturas inscritas.
   - Cada asignatura muestra: código, nombre, sección, y estado "En vivo" / "Sin clase activa".
   - Botón "Entrar a la clase" por cada asignatura.

3. **R3 — Gestión de salas en vivo:**
   - Al "Entrar a la clase", el frontend consulta `GET /api/salas/{room_id}/estado` para saber si hay transmisión activa.
   - Si no hay: el estudiante es **emisor**. Se le pide permiso de micrófono, se conecta a `/ws/sala/{room_id}?rol=emitter&token=...`, y empieza a enviar audio binario.
   - Si hay: el estudiante es **listener**. Se conecta a `/ws/sala/{room_id}?rol=listener&token=...` y recibe subtítulos + señas en tiempo real sin capturar audio.
   - `room_id` se construye como `[COD_RAMO]-[SECCION]` (ej. `INF-221-SEC1`).

4. **R4 — Controles del emisor:**
   - `[Iniciar]` — empieza captura de audio con `getUserMedia` + `MediaRecorder` (WebM/Opus, chunks 250ms) y envío por WebSocket.
   - `[Pausar]` — pausa `MediaRecorder` y deja de enviar audio. El backend deja de emitir segmentos.
   - `[Reanudar]` — reanuda `MediaRecorder` y el envío de audio.
   - `[Finalizar y Guardar]` — detiene la captura, cierra la sala, persiste el timeline en SQLite, notifica a los listeners que la clase terminó.

5. **R5 — Arquitectura pub/sub (fan-out):**
   - `RoomState` en memoria: `emitter_ws`, `listeners_ws` (set), `asr_provider`, `glosario_por_lema`, `sesion_id`, `timeline` (lista en memoria).
   - El audio del emisor se procesa **una sola vez** (ASR + matching). El resultado se envía a `emitter_ws` + todos los `listeners_ws`.
   - Cuando un listener se conecta a una sala activa, recibe los segmentos posteriores a su conexión (no recibe historial de la sesión en curso — eso va en el replay post-clase).
   - Cuando el emisor se desconecta sin "Finalizar y Guardar" (caída de red, cierre de pestaña), la sala se cierra tras un timeout configurable (default 30s) y se guarda el timeline parcial.

6. **R6 — WebSocket unificado `/ws/sala/{room_id}`:**
   - Query params: `?rol=emitter|listener&token=...`.
   - Si `rol=emitter` y la sala no existe → crea la sala, asigna al emisor, inicia ASR.
   - Si `rol=emitter` y la sala ya existe → rechaza con error ("Ya existe una transmisión activa").
   - Si `rol=listener` y la sala no existe → rechaza con error ("No hay transmisión activa").
   - Si `rol=listener` y la sala existe → se une como suscriptor.
   - Eventos salientes (broadcast a emisor + listeners): `{type: "segmento", segment_id, texto, final, senas, timestamp_ms}`.
   - Eventos salientes (control): `{type: "clase_finalizada", clase_id}`.
   - Entrada del emisor: audio binario (chunks WebM/Opus) o texto de control (`{"action": "pausar"}`, `{"action": "reanudar"}`, `{"action": "finalizar"}`).

7. **R7 — Historial (Timeline JSON):**
   - Tabla `clase` (`id` INTEGER PK, `room_id` TEXT, `curso_id` INTEGER FK, `rut_emisor` TEXT FK, `fecha_inicio` TEXT, `fecha_fin` TEXT, `duracion_ms` INTEGER).
   - Tabla `evento_clase` (`id` INTEGER PK, `clase_id` INTEGER FK, `timestamp_ms` INTEGER, `texto` TEXT, `estable` INTEGER, `senas_json` TEXT).
   - Al finalizar, el backend migra el `timeline` en memoria a `evento_clase` y crea el registro en `clase`.
   - `GET /api/historial` (con token) → lista de clases donde el estudiante participó (como emisor o listener inscrito en la sección).
   - `GET /api/historial/{clase_id}` → `{clase: {...}, eventos: [...]}`.

8. **R8 — Vista de historial (PWA):**
   - `HistorialView`: lista de clases pasadas (asignatura, fecha, duración, emisor).
   - `ClaseDetailView` con dos modos:
     - **Modo Apunte/Lectura:** transcripción completa como texto continuo. Señas mostradas como nombres/badges junto al texto.
     - **Modo Simulación (Replay):** reproductor que recorre el timeline según `timestamp_ms`. Subtítulos aparecen progresivamente. Clips de señas se reproducen sincronizados. Controles: Play/Pausa, barra de progreso, velocidad 1x/1.5x/2x.

9. **R9 — Refactor frontend:**
   - Eliminar `Landing.jsx`, `ProfesorView.jsx` (de SPEC-003).
   - Nuevas vistas: `LoginView.jsx`, `DashboardView.jsx`, `SalaView.jsx` (emisor/listener unificado con controles dinámicos), `HistorialView.jsx`, `ClaseDetailView.jsx`.
   - Routing: `#/login` (por defecto si no hay token), `#/dashboard`, `#/sala/{room_id}`, `#/historial`, `#/historial/{clase_id}`.
   - Token persistido en `localStorage`. Redirect a `#/login` si no hay token.
   - `SalaView` detecta su rol (emitter/listener) según el estado de la sala al conectar y muestra controles accordingly.

10. **R10 — Refactor backend:**
    - Reemplazar `/ws/profesor` y `/ws/alumno/{curso_id}` por `/ws/sala/{room_id}`.
    - Eliminar `POST /api/sesiones` (la sesión se crea implícitamente al iniciar la sala).
    - Nuevos endpoints: `/api/auth/login`, `/api/usuario/me`, `/api/salas/{room_id}/estado`, `/api/historial`, `/api/historial/{clase_id}`.
    - Middleware de auth con token.
    - `/health` y `/ws/echo` se mantienen para sanity.

11. **R11 — Seed ampliado:**
    - `seed_glosario.py` extendido para sembrar usuarios, inscripciones y cursos con secciones.
    - Al menos 1 usuario de prueba (RUT, password, nombre) con 2-3 asignaturas inscritas en secciones distintas.
    - Los `curso` ahora incluyen `cod_ramo` (ej. "INF-221") además de `nombre`.

12. **R12 — Tests:**
    - `test_auth.py` — login válido, login inválido, token válido, token expirado/inválido.
    - `test_sala.py` — creación de sala, listener se une, fan-out broadcast, finalizar y guardar timeline.
    - `test_historial.py` — guardar timeline, recuperar timeline, lista de historial.
    - Los tests existentes (`test_matching.py`, `test_schema.py`) se mantienen y pasan.

13. **R13 — Configuración:**
    - `.env` añade: `JWT_SECRET` (para firmar tokens del MVP), `SALA_TIMEOUT_MS` (default 30000), `AUTH_PROVIDER=local` (preparado para `intranet` en el futuro).
    - `docker-compose.yml` mantiene `ASR_PROVIDER=stub` para desarrollo.

14. **R14 — Docker Compose:** `docker compose up --build` levanta todo y el flujo end-to-end funciona: login → dashboard → iniciar clase (stub) → subtítulos + señas → finalizar → ver en historial → replay.

15. **R15 — Verificación mínima:** `ruff check .`, `pytest backend/tests`, `pnpm --prefix frontend build` pasan.

## 5. Diseño técnico

### 5.1 Modelo de datos SQLite (extensiones)

```sql
CREATE TABLE IF NOT EXISTS usuario (
    rut TEXT PRIMARY KEY,
    password_hash TEXT NOT NULL,
    nombre TEXT NOT NULL,
    apellido TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS inscripcion (
    rut TEXT NOT NULL REFERENCES usuario(rut),
    curso_id INTEGER NOT NULL REFERENCES curso(id),
    seccion TEXT NOT NULL,
    PRIMARY KEY (rut, curso_id, seccion)
);

ALTER TABLE curso ADD COLUMN cod_ramo TEXT;
-- (o crear curso desde cero con cod_ramo si es mas limpio)

CREATE TABLE IF NOT EXISTS clase (
    id INTEGER PRIMARY KEY,
    room_id TEXT NOT NULL,
    curso_id INTEGER NOT NULL REFERENCES curso(id),
    seccion TEXT NOT NULL,
    rut_emisor TEXT NOT NULL REFERENCES usuario(rut),
    fecha_inicio TEXT NOT NULL,
    fecha_fin TEXT,
    duracion_ms INTEGER
);

CREATE TABLE IF NOT EXISTS evento_clase (
    id INTEGER PRIMARY KEY,
    clase_id INTEGER NOT NULL REFERENCES clase(id),
    timestamp_ms INTEGER NOT NULL,
    texto TEXT,
    estable INTEGER DEFAULT 0,
    senas_json TEXT
);
```

### 5.2 Estructura de archivos (cambios)

```
backend/
├── app/
│   ├── core/
│   │   ├── config.py          # + JWT_SECRET, SALA_TIMEOUT_MS, AUTH_PROVIDER
│   │   ├── nlp.py
│   │   ├── db.py
│   │   └── auth.py            # NUEVO: token create/verify, middleware
│   ├── asr/                   # sin cambios
│   ├── glossary/              # sin cambios (matching, repository)
│   ├── auth/                  # NUEVO
│   │   ├── __init__.py
│   │   ├── base.py            # AuthProvider interface
│   │   ├── local_provider.py  # LocalAuthProvider (SQLite)
│   │   └── routes.py          # /api/auth/login, /api/usuario/me
│   ├── salas/                 # NUEVO (reemplaza lógica en main.py)
│   │   ├── __init__.py
│   │   ├── manager.py         # RoomManager: registro en memoria, fan-out
│   │   └── routes.py          # /ws/sala/{room_id}, /api/salas/{room_id}/estado
│   ├── historial/             # NUEVO
│   │   ├── __init__.py
│   │   ├── repository.py      # CRUD clase, evento_clase
│   │   └── routes.py          # /api/historial, /api/historial/{clase_id}
│   ├── evaluation/            # sin cambios (logging)
│   └── main.py                # ensamblador: routers + lifespan
├── data/
│   ├── schema.sql             # ampliado
│   └── seed_glosario.json     # ampliado con usuarios + inscripciones
├── scripts/
│   └── seed_glosario.py       # ampliado
└── tests/
    ├── test_matching.py       # sin cambios
    ├── test_schema.py         # ampliado
    ├── test_auth.py           # NUEVO
    ├── test_sala.py           # NUEVO
    └── test_historial.py      # NUEVO
```

```
frontend/
└── src/
    ├── hooks/
    │   ├── useWebSocket.js    # sin cambios
    │   └── useAuth.js         # NUEVO: token, login, logout, persist localStorage
    ├── api/
    │   └── cliente.js         # ampliado: auth, historial, salas
    ├── views/
    │   ├── LoginView.jsx      # NUEVO
    │   ├── DashboardView.jsx  # NUEVO
    │   ├── SalaView.jsx       # NUEVO (emisor/listener unificado)
    │   ├── HistorialView.jsx  # NUEVO
    │   └── ClaseDetailView.jsx# NUEVO (apunte + replay)
    ├── components/
    │   ├── CursoSelector.jsx  # sin cambios (o adaptado)
    │   ├── Subtitulos.jsx     # sin cambios
    │   ├── SenaPlayer.jsx     # sin cambios
    │   ├── EstadoConexion.jsx # sin cambios
    │   ├── ControlesEmisor.jsx # NUEVO: Iniciar/Pausar/Reanudar/Finalizar
    │   └── ReplayPlayer.jsx   # NUEVO: reproductor de timeline
    └── App.jsx                # routing ampliado
```

### 5.3 RoomManager (pub/sub en memoria)

```python
@dataclass
class RoomState:
    room_id: str
    emitter_ws: WebSocket | None = None
    listeners: set[WebSocket] = field(default_factory=set)
    asr_provider: StreamingASRProvider | None = None
    glosario_por_lema: dict = field(default_factory=dict)
    clase_id: int | None = None
    timeline: list[dict] = field(default_factory=list)
    inicio_ms: int = 0
    pausado: bool = False

class RoomManager:
    _salas: dict[str, RoomState] = {}

    @classmethod
    def get_or_create(cls, room_id, curso_id, seccion, rut_emisor) -> RoomState: ...

    @classmethod
    def get(cls, room_id) -> RoomState | None: ...

    @classmethod
    async def broadcast(cls, room_id, evento: dict) -> None:
        sala = cls._salas.get(room_id)
        if not sala: return
        texto = json.dumps(evento)
        targets = [sala.emitter_ws] + list(sala.listeners) if sala.emitter_ws else list(sala.listeners)
        for ws in targets:
            if ws: await ws.send_text(texto)

    @classmethod
    async def finalizar(cls, room_id) -> int | None:
        # persist timeline to SQLite, remove room, return clase_id
        ...
```

### 5.4 WebSocket `/ws/sala/{room_id}`

```python
@app.websocket("/ws/sala/{room_id}")
async def ws_sala(ws: WebSocket, room_id: str, rol: str = Query("listener"), token: str = Query("")):
    # validar token, obtener rut
    # si rol=emitter:
    #   si sala existe → rechazar
    #   crear sala, asignar emitter, iniciar ASR
    # si rol=listener:
    #   si sala no existe → rechazar
    #   unirse como listener
    # loop: recibir audio (emitter) o nada (listener)
    #       procesar con ASR + matching
    #       broadcast a todos
    #       acumular en timeline
    # al cerrar: si emitter, finalizar y guardar tras timeout
```

### 5.5 Auth (JWT simple para MVP)

```python
# app/core/auth.py
import jwt, time

def crear_token(rut: str, secret: str) -> str:
    return jwt.encode({"rut": rut, "exp": int(time.time()) + 3600}, secret, algorithm="HS256")

def verificar_token(token: str, secret: str) -> str | None:
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        return payload["rut"]
    except jwt.InvalidTokenError:
        return None
```

### 5.6 ReplayPlayer (frontend)

```jsx
function ReplayPlayer({ eventos }) {
  const [pos, setPos] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [velocidad, setVelocidad] = useState(1)

  useEffect(() => {
    if (!playing) return
    const timer = setInterval(() => {
      setPos(p => {
        if (p >= eventos.length - 1) { setPlaying(false); return p }
        return p + 1
      })
    }, (eventos[pos + 1]?.timestamp_ms - eventos[pos]?.timestamp_ms) / velocidad || 100)
    return () => clearInterval(timer)
  }, [playing, pos, velocidad])

  // render: subtítulos hasta pos, video de seña si eventos[pos].senas
}
```

### 5.7 Configuración (`.env.example` ampliado)

```
PORT=8000
ASR_PROVIDER=stub
GOOGLE_APPLICATION_CREDENTIALS=
SPACY_MODEL=es_core_news_md
DB_PATH=data/glosario.db
STUB_INTERVAL_MS=1500
JWT_SECRET=cambiar-en-produccion
SALA_TIMEOUT_MS=30000
AUTH_PROVIDER=local
```

## 6. Criterios de aceptación

- [ ] R1–R15 satisfechos.
- [ ] Login con RUT + contraseña funciona; token se persiste en localStorage.
- [ ] Dashboard muestra asignaturas inscritas con estado "En vivo" / "Sin clase".
- [ ] Emisor: iniciar → subtítulos + señas aparecen; pausar → se detiene; reanudar → continúa; finalizar → se guarda.
- [ ] Listener: se une a sala activa y recibe subtítulos + señas en tiempo real.
- [ ] Fan-out: con 2+ clientes en la misma sala, el ASR procesa una sola vez y todos reciben el broadcast.
- [ ] Secciones simultáneas: dos salas con mismo ramo y distinta sección son aisladas.
- [ ] Historial: tras finalizar, la clase aparece en el historial.
- [ ] Modo Apunte: transcripción completa en texto continuo.
- [ ] Modo Replay: reproducción sincronizada de subtítulos + señas con controles Play/Pausa/velocidad.
- [ ] `ruff check .` pasa.
- [ ] `pytest backend/tests` pasa (tests nuevos + existentes).
- [ ] `pnpm --prefix frontend build` pasa.
- [ ] `docker compose up --build` levanta todo y el flujo end-to-end funciona con stub.

## 7. Tareas de implementación

1. **Backend — Modelo de datos:** ampliar `schema.sql` con `usuario`, `inscripcion`, `clase`, `evento_clase`, `cod_ramo` en `curso`.
2. **Backend — Auth:** implementar `core/auth.py` (JWT), `auth/base.py` (AuthProvider), `auth/local_provider.py`, `auth/routes.py` (`/api/auth/login`, `/api/usuario/me`).
3. **Backend — Salas:** implementar `salas/manager.py` (RoomManager, RoomState, broadcast, finalizar) y `salas/routes.py` (`/ws/sala/{room_id}`, `/api/salas/{room_id}/estado`).
4. **Backend — Historial:** implementar `historial/repository.py` (CRUD clase/evento_clase) y `historial/routes.py` (`/api/historial`, `/api/historial/{clase_id}`).
5. **Backend — main.py:** ensamblar nuevos routers, middleware de auth, mantener `/health` y `/ws/echo`.
6. **Backend — Seed:** ampliar `seed_glosario.json` y `seed_glosario.py` con usuarios, inscripciones, `cod_ramo`.
7. **Backend — Tests:** `test_auth.py`, `test_sala.py`, `test_historial.py`; ampliar `test_schema.py`.
8. **Frontend — Auth:** `useAuth.js` (token, login, logout), `LoginView.jsx`.
9. **Frontend — Dashboard:** `DashboardView.jsx` con lista de asignaturas y estado de sala.
10. **Frontend — Sala:** `SalaView.jsx` (emisor/listener unificado) + `ControlesEmisor.jsx`.
11. **Frontend — Historial:** `HistorialView.jsx` + `ClaseDetailView.jsx` (apunte + replay) + `ReplayPlayer.jsx`.
12. **Frontend — Routing:** actualizar `App.jsx` con nuevas rutas y protección de auth.
13. **Frontend — API:** ampliar `cliente.js` con auth, salas, historial.
14. **Config:** actualizar `.env.example`, `docker-compose.yml`, `requirements.txt` (PyJWT, bcrypt).
15. **Verificar:** `ruff`, `pytest`, `pnpm build`, `docker compose up --build`, smoke end-to-end.
16. **Documentación:** actualizar `docs/historial_implementacion.md` al commitear.

## 8. Verificación

```powershell
# Backend
cd backend
.\venv\Scripts\activate
pip install -r requirements.txt
python scripts\seed_glosario.py
pytest tests -v
ruff check .
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
pnpm install
pnpm dev
# abrir http://localhost:5173
# login con RUT de prueba → dashboard → entrar a clase → subtítulos + señas
# finalizar → historial → replay

# Docker
docker compose up --build
# mismo flujo en http://localhost:5173
```

## 9. Notas / decisiones diferidas

- **Hash de passwords:** para el MVP se usa `sha256(salt + password)` o bcrypt. Si se usa bcrypt, añadir `bcrypt` a `requirements.txt`. Decisión diferida a implementación.
- **SSO/OAuth2:** la interfaz `AuthProvider` con `LocalAuthProvider` deja el camino abierto para `IntranetAuthProvider` que haga redirect a la Intranet real. No se implementa en esta spec.
- **Timeout de sala:** si el emisor se desconecta abruptamente, la sala se cierra tras `SALA_TIMEOUT_MS` (30s) y se guarda el timeline parcial. Se podría implementar un "reclamar emisor" (otro alumno toma el control) en una spec posterior.
- **Listeners tardíos:** un listener que se une a una sala en curso no recibe los segmentos previos de esa sesión — solo los posteriores. El historial completo queda disponible tras finalizar la clase. Se podría implementar "catch-up" (enviar timeline parcial al unirse) en una spec posterior si se considera necesario.
- **`Sesion`/`Segmento` vs `Clase`/`Evento_clase`:** las tablas de SPEC-002 (`sesion`, `segmento`) se mantienen por compatibilidad o se migran. Preferencia: migrar a `clase`/`evento_clase` para mayor claridad semántica, pero se puede mantener ambas si facilita la transición.
- **Replay en tiempo real:** el replay usa `setTimeout`/`setInterval` para simular los `timestamp_ms`. No es preciso a nivel de milisegundos pero suficiente para el piloto. Si se necesita precisión, usar `requestAnimationFrame` con compensación de drift.
- **Migración de SPEC-002/SPEC-003:** las vistas `ProfesorView` y `Landing` se eliminan. El WebSocket `/ws/profesor` y `/ws/alumno/{curso_id}` se eliminan. Los endpoints `/api/cursos` y `/api/sesiones` se modifican o eliminan. Esto es un breaking change intencional — el sistema cambia de paradigma.

### Specs siguientes (propuesta)
- SPEC-005 — Piloto de evaluación: WER (jiwer), latencia end-to-end, SUS (si se retoma el plan de evaluación original).
- SPEC-006 — Integración SSO/OAuth2 con Intranet real.
- SPEC-007 — Módulo secundario alumno→profesor (MediaPipe + DTW/k-NN).