# SPEC-009 — Acceso por inscripción, permiso de captura, estado de sesión y saneamiento

**Etapa del plan:** Semestre 2 · Etapa 5 (integración) de `docs/plan_desarrollo_tecnico.md`, como corrección de SPEC-004 y SPEC-005. Informe: RF01, RF05, RF08, RF09, RF11, RF21, RF22, RN02, RN13, RN14, RN15, RNF10, RNF11, CA01, CA02 y §3.7.
**Estado:** Completada
**Depende de:** SPEC-005; SPEC-007 para los requisitos de clips (R6–R8)

---

## 1. Objetivo

Cerrar las contradicciones entre el prototipo y la especificación del informe que no dependen de nuevas capacidades: quién puede entrar y emitir en una sala, qué ven los oyentes cuando la captura se pausa o se corta, cómo se guardan las credenciales, y el estado de la documentación y del código heredado.

## 2. Contexto y supuestos

- **Hallazgos de acceso** (comprobados el 2026-11-16 con `TestClient` sobre una base temporal):
  - Un usuario autenticado que **no** está inscrito recibe los segmentos de la sala `INF-221-1` como oyente.
  - Ese mismo usuario puede abrir como emisor la sala `INF-221-999`, de una sección que no existe, y se crea una clase. `ws_sala` (`main.py:97-123`) solo valida el token y que exista el `cod_ramo`.
  - `GET /api/cursos/{id}/glosario` responde 200 a un usuario no inscrito.
  - `GET /data/videos_senas/<archivo>` responde 200 sin token.
  - Contradicen RF11, RN13 y CA01 ("las tres operaciones se rechazan").
- **Hallazgos de sesión:**
  - El rol se decide por orden de llegada: quien entra a una sala sin transmisión es emisor (`SalaView.jsx:90-95`). El informe reserva la captura a un responsable autorizado (RN02).
  - La pausa es solo local (`recorder.pause()`): el servidor no conoce el estado y los oyentes no ven nada (RF08). No queda registro de la discontinuidad (RF09, RN14).
  - Una clase cerrada por desconexión del emisor queda igual que una cerrada explícitamente; el historial no permite distinguirlas (RF22).
  - No existe el aviso de condiciones de registro previo a la captura (RF05).
  - El token dura 1 hora (`core/auth.py:14`). Una clase de 90 minutos lo supera y cualquier 401 posterior expulsa al usuario al login.
  - `GET /api/salas/{room_id}/estado` devuelve `rut_emisor`, que ningún componente del frontend usa.
- **Hallazgos de seguridad:**
  - Contraseñas con SHA-256 y una sal fija en el código (`core/auth.py`), duplicada en `scripts/seed_glosario.py`. RNF10 pide funciones de derivación.
  - `JWT_SECRET` tiene un valor por defecto conocido (`cambiar-en-produccion`) y `docker-compose.yml` no lo define.
  - CORS con `allow_origins=["*"]` y `allow_credentials=True`.
- **Hallazgos de mantenimiento:**
  - Sin uso: `/ws/echo`, `evaluation/logging.py` y sus tablas `sesion` y `segmento`, `list_cursos`, `insert_curso` e `insert_termino` (solo los llama `test_schema.py`), `RoomState.timeline` e `inicio_ms`, `AUTH_PROVIDER`, y `fetchCursos` en `api/cliente.js`.
  - `README.md` dice "Etapa 1", enlaza a `docs/README.md` (no existe) y documenta el WebSocket de eco. `AGENTS.md` dice "No existe todavía suite de tests".
  - El prototipo se aparta del informe en varias decisiones (SQLite, JavaScript, captura a cargo del estudiante, ASR local) sin dejarlo escrito.
- **Decisión sobre roles:** se mantiene el modelo centrado en el estudiante de SPEC-004. El informe habla de "el docente o un responsable de captura": el estudiante puede ser ese responsable, siempre que el permiso sea explícito y no por orden de llegada.
- La base local es descartable; los cambios de esquema se aplican recreándola con el seed.

## 3. Alcance

### Incluido

1. Autorización por inscripción en el WebSocket de sala, el glosario, el estado de sala y los clips.
2. Permiso de captura por inscripción.
3. Pausa y reanudación conocidas por el servidor y visibles para los oyentes.
4. Registro de discontinuidades y marca de registro incompleto en el historial.
5. Aviso de condiciones antes de capturar.
6. Derivación de contraseñas, secreto y duración del token, CORS.
7. Eliminación de código y tablas sin uso.
8. README, `AGENTS.md`, `.env.example` y registro de decisiones técnicas.

### Explícitamente fuera

- Administración de usuarios, cursos y permisos desde la aplicación (RF02, RF03): siguen saliendo del seed.
- Roles de colaborador lingüístico, administrador y soporte.
- Reconexión del emisor a la misma clase y recuperación de eventos para oyentes que entran tarde o se reconectan (RF20).
- Auditoría de operaciones, conservación y eliminación (RF28, RF29).
- Inicio de sesión institucional.
- Renovación automática del token.

## 4. Requisitos

**Acceso**

1. **R1 — Sala por inscripción:** `/ws/sala/{room_id}` rechaza la conexión si el RUT del token no tiene una inscripción en el curso y la sección de la sala. Envía `{type: "error", mensaje: "No tienes acceso a esta sala"}` y cierra, sin crear sala ni clase. Como consecuencia, una sección sin inscritos no puede abrirse.
2. **R2 — Permiso de captura:** `inscripcion.puede_capturar` indica quién puede emitir. Conectarse con `rol=emitter` sin ese permiso se rechaza con "No tienes permiso de captura en esta sala".
3. **R3 — REST por inscripción:** `GET /api/cursos/{id}/glosario` y `GET /api/salas/{room_id}/estado` responden 403 a quien no esté inscrito. El estado de sala deja de devolver `rut_emisor`.
4. **R4 — Cursos con permiso:** `GET /api/cursos` incluye `puede_capturar` por cada inscripción.
5. **R5 — Interfaz según permiso:** el dashboard ofrece "Iniciar Transmisión" solo con permiso de captura. Sin permiso y sin clase activa muestra "Sin clase activa" sin botón de inicio. `SalaView` no asume el rol de emisor sin permiso: muestra "Aún no hay una transmisión en esta sala" y el botón de volver.
6. **R6 — Clips protegidos:** los clips se sirven por `GET /api/cursos/{curso_id}/senas/{termino_id}/video`, que exige token e inscripción y responde 404 si el término está retirado. Se elimina el montaje público `/data/videos_senas` y su `location /data/` en nginx.
7. **R7 — Reproductor con token:** `SenaPlayer` obtiene cada clip con `Authorization: Bearer` y lo reproduce desde una URL de objeto. Los clips ya descargados se reutilizan durante la sesión.
8. **R8 — Precarga:** al entrar a una sala, el cliente descarga en segundo plano los clips del glosario del curso. Un fallo de precarga no interrumpe la sala.

**Estado de sesión**

9. **R9 — Pausa en el servidor:** el emisor envía `{action: "pausar"}` y `{action: "reanudar"}`. El servidor mantiene el estado de la sala (`activa` o `pausada`), descarta las tramas de audio que lleguen en pausa, cierra el segmento abierto y difunde `{type: "estado_sesion", estado, timestamp_ms}`.
10. **R10 — Pausa visible:** los oyentes ven "Transmisión en pausa" mientras dure. Quien se une a una sala recibe el estado vigente al conectarse.
11. **R11 — Discontinuidades registradas:** las pausas, reanudaciones y la desconexión del emisor se guardan como filas de `evento_clase` con `tipo` (`pausa`, `reanudacion`, `desconexion`). Las transcripciones tienen `tipo = "segmento"`.
12. **R12 — Tipo de cierre:** `clase.cierre` vale `explicito` o `timeout`.
13. **R13 — Historial con interrupciones:** el detalle de la clase muestra las pausas y la desconexión como separadores con su marca de tiempo. El listado marca "Registro incompleto" cuando `cierre = "timeout"`. El conteo de palabras y la vista previa consideran solo eventos de tipo `segmento`. El replay salta los separadores sin detenerse.
14. **R14 — Aviso de condiciones:** antes de pedir el micrófono, el emisor ve qué se registra (texto transcrito y eventos de señas; el audio no se guarda), quién puede consultarlo (inscritos en la sección) y que aún no hay una política institucional de conservación. Debe confirmar para continuar. El texto indica que el aviso no reemplaza la autorización del curso (RN15).
15. **R15 — Confirmación exigida por el servidor:** la conexión como emisor requiere `condiciones=1`; sin ese parámetro se rechaza. La clase guarda `condiciones_confirmadas = 1`.

**Seguridad**

16. **R16 — Derivación de contraseñas:** las contraseñas se guardan con `hashlib.scrypt` y una sal aleatoria por usuario, en un formato que incluye parámetros y sal. La comparación usa `hmac.compare_digest`. El seed importa la función de `app.core.auth`; no hay sal fija ni función duplicada.
17. **R17 — Secreto del token:** desaparece el valor por defecto conocido. Si `JWT_SECRET` está vacío, el proceso genera uno aleatorio al arrancar y registra un `logger.warning` que explica que las sesiones no sobreviven a un reinicio. `docker-compose.yml` lo toma del `.env` de la raíz. Las pruebas usan secretos de al menos 32 bytes.
18. **R18 — Duración del token:** `JWT_EXP_MIN` (por defecto 480) define la vigencia, suficiente para una jornada de clases.
19. **R19 — CORS acotado:** `CORS_ORIGINS` (por defecto `http://localhost:5173`) reemplaza al comodín, con `allow_credentials=False`. En Docker las peticiones son del mismo origen a través de nginx.

**Saneamiento**

20. **R20 — Código sin uso:** se eliminan `/ws/echo`, `evaluation/logging.py` con las tablas `sesion` y `segmento` (si SPEC-008 no lo hizo), `list_cursos`, `insert_curso`, `insert_termino`, `RoomState.timeline`, `RoomState.inicio_ms`, `AUTH_PROVIDER` y `fetchCursos`. Las pruebas que dependían de ellos se reescriben contra el código vigente.
21. **R21 — README vigente:** describe el estado real del prototipo, los modos de ejecución actuales (nativo, Docker con HTTPS, túnel de Cloudflare), los usuarios de prueba, las variables de entorno y qué es de ensayo. No enlaza a archivos inexistentes ni menciona el WebSocket de eco.
22. **R22 — AGENTS.md y `.env.example` vigentes:** `AGENTS.md` deja de afirmar que no hay pruebas. `.env.example` lista todas las variables que lee `core/config.py` y ninguna que ya no exista.
23. **R23 — Decisiones técnicas:** `docs/decisiones_tecnicas.md` registra cada decisión del prototipo que difiere del informe o del plan, con lo que decía el documento, lo que hace el prototipo y el motivo.
24. **R24 — Pruebas:** se agregan pruebas de: oyente no inscrito rechazado, sección inexistente rechazada, emisor sin permiso rechazado, glosario y estado con 403, clip con 401 sin token y 403 sin inscripción, pausa difundida y tramas descartadas en pausa, estado enviado al unirse, eventos de discontinuidad, `cierre` explícito y por timeout, emisor sin `condiciones` rechazado, y verificación de contraseñas con scrypt.
25. **R25 — Verificación mínima:** `ruff check backend`, `pytest backend/tests` y `pnpm --prefix frontend build` pasan sin errores.

## 5. Diseño técnico

### 5.1 Esquema

```sql
-- inscripcion
puede_capturar INTEGER NOT NULL DEFAULT 0

-- clase
cierre TEXT,                                   -- explicito | timeout
condiciones_confirmadas INTEGER NOT NULL DEFAULT 0

-- evento_clase
tipo TEXT NOT NULL DEFAULT 'segmento'          -- segmento | pausa | reanudacion | desconexion
```

Seed: tres usuarios de prueba. Uno con permiso de captura en el curso piloto, uno inscrito sin permiso y uno sin inscripción en el curso piloto, para las pruebas negativas.

### 5.2 Autorización

`app/core/permisos.py` (nuevo):

```python
def inscripcion(rut: str, curso_id: int, seccion: str) -> dict | None: ...
def exigir_inscripcion(rut: str, curso_id: int, seccion: str) -> dict:   # HTTPException 403
def resolver_sala(room_id: str) -> tuple[int, str] | None:               # curso_id, seccion
```

- `ws_sala`: tras validar el token, `resolver_sala` e `inscripcion`. Para `emitter`, además `puede_capturar` y `condiciones == "1"`. Se conserva el patrón actual de aceptar, enviar el error y cerrar, para que el cliente pueda mostrar el mensaje.
- `historial/repository.usuario_participa` se reemplaza por `inscripcion`.

### 5.3 Clips

```python
@router.get("/api/cursos/{curso_id}/senas/{termino_id}/video")
def video_sena(request: Request, curso_id: int, termino_id: int) -> FileResponse: ...
```

- Verifica token, inscripción en el curso (cualquier sección), que el término sea de ese curso y que no esté retirado. La ruta del archivo se toma de la base, nunca de la URL.
- Las señas difundidas y las del glosario llevan `video_url` con esta ruta.
- Cliente: `frontend/src/api/clips.js` con `obtenerClip(url)` que hace `fetch` con el token, crea la URL de objeto y la guarda en un `Map`; `precargar(glosario)` recorre el glosario sin bloquear. Las URL de objeto se liberan al salir de la sala.

### 5.4 Estado de sesión

- `RoomState.estado: str = "activa"`.
- `_receiver`: ante `pausar` o `reanudar` actualiza el estado, guarda el evento de discontinuidad y difunde `estado_sesion`. En pausa no encola tramas; al pausar encola la señal de vaciado del segmento abierto (SPEC-006).
- Al agregar un oyente se le envía `estado_sesion` con el estado vigente.
- En el cierre: `cierre = "explicito"` si llegó `finalizar`; en otro caso se guarda el evento `desconexion` y `cierre = "timeout"`.
- `guardar_evento` recibe `tipo`. `listar_clases` y `obtener_eventos` devuelven `cierre` y `tipo`.

### 5.5 Frontend

```
frontend/src/
├── api/clips.js                    # NUEVO
├── components/
│   ├── CondicionesModal.jsx        # NUEVO: aviso y confirmación (R14)
│   └── SenaPlayer.jsx              # clip desde URL de objeto
└── views/
    ├── DashboardView.jsx           # botones según puede_capturar
    ├── SalaView.jsx                # rol según permiso; pausar/reanudar por WS; banner de pausa; precarga
    ├── HistorialView.jsx           # marca "Registro incompleto"
    └── ClaseDetailView.jsx         # separadores de pausa y desconexión
```

`SalaView` necesita `puede_capturar` de la sala: lo obtiene de la respuesta de `GET /api/salas/{room_id}/estado`, que pasa a incluir `puede_capturar` del solicitante en lugar de `rut_emisor`.

### 5.6 Seguridad

```python
def hash_password(password: str) -> str:
    sal = os.urandom(16)
    derivada = hashlib.scrypt(password.encode(), salt=sal, n=2**14, r=8, p=1)
    return f"scrypt$16384$8$1${b64(sal)}${b64(derivada)}"

def verificar_password(password: str, guardado: str) -> bool: ...
```

- `auth/routes.login` usa `verificar_password`.
- `core/config.py`: `JWT_SECRET: str = ""`, `JWT_EXP_MIN: int = 480`, `CORS_ORIGINS: str = "http://localhost:5173"`. El secreto efectivo se resuelve una vez en `get_settings`.
- `docker-compose.yml`: `JWT_SECRET=${JWT_SECRET:-}` y `CORS_ORIGINS=${CORS_ORIGINS:-}`.

### 5.7 `docs/decisiones_tecnicas.md`

Tabla con una fila por decisión. Contenido mínimo:

| Tema | Informe o plan | Prototipo | Motivo |
|---|---|---|---|
| Base de datos | PostgreSQL como alternativa inicial | SQLite | volumen de la PoC; el informe deja la selección abierta |
| Lenguaje del cliente | TypeScript | JavaScript con React | velocidad de prototipado |
| Responsable de captura | docente o responsable | estudiante con permiso de captura | SPEC-004: el docente no opera la plataforma |
| ASR | adaptador local y remoto | faster-whisper local | sin credenciales ni envío de voz a terceros (SPEC-006) |
| Clips | banco validado | tarjetas de ensayo | sin validación lingüística aún (SPEC-007) |
| Mensajería | Pub/Sub con posible intermediario | distribuidor en memoria en un proceso | suficiente para la PoC; sin recuperación de eventos |

`docs/decisiones_tecnicas.md` es un archivo nuevo dentro de `docs/`, que el plan destina a la documentación del proyecto.

## 6. Criterios de aceptación

- [x] R1–R25 satisfechos.
- [x] CA01 del informe: un usuario de otro curso intenta la API del glosario, un clip y la suscripción a la sala; las tres se rechazan.
- [x] El usuario sin permiso de captura no ve "Iniciar Transmisión" y, si fuerza la URL de la sala, no puede emitir.
- [x] Al pausar el emisor, un segundo dispositivo oyente muestra "Transmisión en pausa" y deja de recibir texto; al reanudar, vuelve.
- [x] Un oyente que entra durante una pausa ve el estado de pausa.
- [x] El detalle de una clase con una pausa muestra el separador; una clase cerrada por desconexión aparece como "Registro incompleto".
- [x] No se puede iniciar la captura sin confirmar el aviso de condiciones.
- [x] Los clips se reproducen en vivo y en replay, y `GET` directo a un clip sin token responde 401.
- [x] Una sesión iniciada sigue válida después de 90 minutos.
- [x] En la base no hay hashes SHA-256 de contraseñas; dos usuarios con la misma contraseña tienen valores guardados distintos.
- [x] El README permite levantar el proyecto desde cero siguiendo solo sus pasos.

## 7. Tareas de implementación

1. `schema.sql` y seed: columnas nuevas, tres usuarios, permisos.
2. `core/permisos.py`; aplicar en `ws_sala`, glosario, estado de sala e historial.
3. Endpoint de clips; retirar el montaje estático y el `location /data/` de nginx.
4. `core/auth.py`: scrypt, verificación, duración del token; `core/config.py`: secreto, CORS.
5. `salas/manager.py` y `main.py`: estado de sesión, acciones de pausa, eventos de discontinuidad, tipo de cierre, condiciones.
6. `historial/`: `tipo` y `cierre` en repositorio y rutas.
7. Frontend: `api/clips.js`, `SenaPlayer`, `CondicionesModal`, `DashboardView`, `SalaView`, `HistorialView`, `ClaseDetailView`, estilos.
8. Eliminación del código sin uso (R20).
9. Pruebas (R24).
10. `README.md`, `AGENTS.md`, `.env.example`, `docker-compose.yml`, `docs/decisiones_tecnicas.md`.
11. Verificación de §8 y entrada en `docs/historial_implementacion.md`.

## 8. Verificación

```powershell
ruff check backend
pytest backend/tests
pnpm --prefix frontend build

cd backend
.\venv\Scripts\activate
python scripts\seed_glosario.py
uvicorn app.main:app --port 8000
# en otra terminal: cd frontend; pnpm dev

# Manual:
#   usuario con permiso → "Iniciar Transmisión" → aviso de condiciones → confirmar → captura
#   usuario sin permiso (otra ventana) → sin botón de inicio; entra como oyente a la clase activa
#   emisor pausa → oyente ve "Transmisión en pausa"; reanuda → vuelve el texto
#   cerrar la pestaña del emisor → tras el timeout la clase figura como "Registro incompleto"
#   usuario sin inscripción → no ve el curso; forzar #/sala/INF-221-1 → "No tienes acceso a esta sala"
#   abrir la URL de un clip sin token → 401
```

## 9. Notas / decisiones diferidas

- **Si el tiempo no alcanza,** lo mínimo de esta spec es R1–R5 (acceso y permiso de captura) y R21–R23 (documentación). El resto puede pasar a una spec posterior sin dejar el sistema inconsistente, salvo R6–R8, que deben ir juntos.
- **Reconexión del emisor:** hoy, si el emisor pierde la conexión, la clase se cierra tras `SALA_TIMEOUT_MS` y un reintento dentro de esa ventana recibe "Ya existe una transmisión activa". Retomar la misma clase exige separar el ciclo de vida de la sala del WebSocket del emisor; queda para Proyecto de Título junto con la recuperación de eventos por número de secuencia (RF20, RNF07).
- **Token en la URL del WebSocket:** se mantiene porque el navegador no permite cabeceras en `WebSocket`. nginx no debe registrar la cadena de consulta de `/ws/` en un despliegue real.
- **Roles restantes del informe** (colaborador, administrador, soporte) y la administración desde la aplicación quedan para Proyecto de Título.
- **Texto del aviso de condiciones:** es provisional. La versión definitiva depende de la política que acuerden la institución y PIESDI.
