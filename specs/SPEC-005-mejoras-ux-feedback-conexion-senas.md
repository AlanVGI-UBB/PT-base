# SPEC-005 — Mejoras de UX: feedback de conexión, reproducción de señas y errores visibles

**Etapa del plan:** Semestre 2 · Etapa 5 (interfaz del alumno + integración) — mejoras de usabilidad sobre el entregable de SPEC-004.
**Estado:** Completada — verificado (ruff, pytest 29/29, build frontend OK)
**Depende de:** SPEC-003, SPEC-004

---

## 1. Objetivo

Resolver los hallazgos de la auditoría de flujos y UX del sistema completo (login → dashboard → sala en vivo → historial → replay): dar feedback real de conexión y errores, reproducir efectivamente los videos de las señas, eliminar controles muertos y estados falsos, y sanear código huérfano. No introduce funcionalidad nueva de dominio: solo corrige la experiencia de uso del flujo ya construido.

## 2. Contexto y supuestos

- **Auditoría base:** se realizó una revisión de los flujos de uso y UX sobre el código actual (`frontend/src/**`, `backend/app/**`). Los hallazgos que aborda esta spec son: sin indicador de estado de conexión en la sala (`estadoWs` se setea pero nunca se renderiza en `SalaView.jsx:95,131-133`); el evento `clase_finalizada` (`backend/app/main.py:204`) no tiene handler en el frontend y el WS del listener se cierra en silencio tras 30s (`main.py:222`); los videos de señas (`video_url`) se descartan y solo se muestra una tarjeta de texto (`SalaView.jsx:315-322`, `ClaseDetailView.jsx:247-254`); errores silenciosos en entrar a sala (`SalaView.jsx:160-162`) y al denegar el micrófono (`SalaView.jsx:195-197`); controles muertos (gear, Expandir, Más opciones, filtro de fecha del historial en `HistorialView.jsx:166-173`); estados falsos ("Micrófono Conectado" estático en `DashboardView.jsx:86-89`, "Audio y video sincronizados" en `SalaView.jsx:353`); "Cargando..." infinito en `ClaseDetailView.jsx:153-159`; sin normalización de RUT en login; token expira a la hora (`core/auth.py:13`) sin manejo UX; endpoints REST usan `?rut=` en vez de token (desviación de SPEC-004 R10); código huérfano de SPEC-003; `tiempo` del emisor calculado pero no mostrado.
- **Stack heredado:** React 18 + Vite 5 + PWA, hash routing manual, sin React Router; backend FastAPI + SQLite, `RoomManager` en memoria (`salas/manager.py`).
- **Videos de señas:** se sirven desde `/data/videos_senas/` (`main.py:46`). Los clips actuales son placeholders sin contenido real; el reproductor debe quedar funcional para reemplazarlos por los clips reales sin tocar código.
- **`SALA_TIMEOUT_MS` ya existe** en configuración (`core/config.py:17`, default 30000) pero no se usa: hoy el emisor que se desconecta sin "Finalizar y Guardar" provoca el cierre inmediato de la sala (`main.py:197-207`), distinto a lo que pedía SPEC-004 R5 (cierre tras timeout con timeline parcial).
- **Audiencia:** estudiantes sordos. Todo el feedback es visual; los errores silenciosos o avisos no visibles se consideran fallas graves de esta spec.
- El audio de la clase sigue sin guardarse (solo timeline JSON) — sin cambios.

## 3. Alcance

### Incluido

1. **Reproducción de señas (en vivo y replay):** componente `SenaPlayer` integrado en `SalaView` y `ClaseDetailView`, reproduciendo `video_url` con rótulo `texto_visible`, autoplay/muted/loop y fallback ante error de carga.
2. **Feedback de conexión en sala:** indicador visible conectado / desconectado / reconectando, reconexión con backoff exponencial y reintento manual al agotar intentos.
3. **Eventos de control del backend en el frontend:** handler de `clase_finalizada` (aviso al listener + retorno al dashboard) y de `emisor_desconectado`.
4. **Errores visibles:** todos los errores de WS (`{type:"error"}`), REST (401/404/500) y permisos de micrófono se muestran al usuario en español; sin redirecciones silenciosas.
5. **Dashboard:** estado real "En vivo" / "Sin clase activa" por asignatura (el fetch ya existe, `DashboardView.jsx:56-63`, pero no se renderiza), botón dinámico ("Entrar a la clase" / "Iniciar Transmisión de Clase"), eliminación del badge falso "Micrófono Conectado", diferenciación entre error de carga y lista vacía.
6. **Tiempo transcurrido visible** para el emisor durante la transmisión (mm:ss).
7. **Eliminación de controles muertos:** gear de Configuración, Expandir, Más opciones (sin handler) y filtro de fecha del historial (sin funcionalidad).
8. **Estado de error en detalle de clase** (clase no encontrada / carga fallida), sin "Cargando..." infinito.
9. **Login:** normalización de RUT (puntos/guión opcionales, DV correcto) antes de enviar; mensajes de error claros.
10. **Sesión expirada:** cualquier 401 (REST) o token inválido (WS) limpia la sesión y redirige a login con mensaje "Sesión expirada, inicia sesión nuevamente".
11. **Persistencia del tamaño de fuente** A+/A− (localStorage) en `SalaView` y `ClaseDetailView`.
12. **Accesibilidad:** `aria-label` en botones solo-icono, tabs de navegación como `<button>`, foco visible.
13. **Backend — cierre de salas:** al finalizar (explícito o por timeout), se difunde `clase_finalizada` y se cierran los WebSockets de los listeners (hoy quedan colgados 30s en silencio, `main.py:219-226`).
14. **Backend — timeout de emisor:** si el emisor se desconecta sin "Finalizar y Guardar", se avisa a los listeners y la sala se cierra tras `SALA_TIMEOUT_MS` guardando el timeline parcial (cumple SPEC-004 R5).
15. **Auth real en REST:** endpoints protegidos validan el token (`Authorization: Bearer`); se elimina el uso de `?rut=` del frontend; `GET /api/historial/{clase_id}` valida que el solicitante esté inscrito en la sección (hoy cualquier usuario autenticado puede leer cualquier clase por id, `historial/repository.py:67-78`).
16. **Limpieza de código huérfano:** eliminar `Landing.jsx`, `ProfesorView.jsx`, `AlumnoView.jsx`, `CursoSelector.jsx`, `Subtitulos.jsx`, `EstadoConexion.jsx`, `ControlesEmisor.jsx` (sin uso desde SPEC-004); reutilizar `SenaPlayer.jsx` (mejorado).

### Explícitamente fuera

- Videos reales del banco de señas (tarea del autor del proyecto, fuera de la app).
- Tema claro/oscuro.
- Exportación del timeline a PDF u otros formatos.
- Notificaciones push.
- Catch-up de timeline para listeners tardíos (ya diferido en SPEC-004 §9).
- "Reclamar emisor" (otro estudiante retoma la transmisión tras desconexión) — solo se avisa y se cierra con timeout.
- Integración SSO/OAuth2 real de la Intranet.
- Cálculo de WER/SUS/piloto de evaluación (→ SPEC futura).

## 4. Requisitos

1. **R1 — Reproducción de señas en vivo:** al recibir un segmento `final=true` con `senas` no vacío, `SalaView` reproduce el video de la seña principal (`senas[0].video_url`) en el panel lateral con `<video autoPlay muted loop>`, rótulo con `texto_visible` y borde destacado del término en el subtítulo. Si el video falla al cargar (`onError`), muestra "Video no disponible" en el panel, sin romper el flujo.
2. **R2 — Reproducción de señas en replay:** en `ClaseDetailView` modo replay, el video de la seña del evento actual se reproduce sincronizado (mismo `SenaPlayer`); en modo apunte solo se muestran los badges/nombres de las señas (sin videos).
3. **R3 — Estado de conexión visible:** `SalaView` muestra un indicador con tres estados — conectado / reconectando / desconectado — junto al título de la sala. El badge "EN VIVO" solo se muestra en estado conectado.
4. **R4 — Reconexión con backoff:** el hook `useWebSocket` implementa reintentos con esperas 3s → 6s → 12s → 24s (máx. 5 intentos) y expone `estado` y `intentos`; al agotar los intentos se muestra un mensaje de error con botón "Reintentar". El cierre de pestaña cancela la reconexión.
5. **R5 — `clase_finalizada` en el frontend:** el listener recibe el evento y ve un aviso visible ("La clase terminó y se guardó en tu historial") seguido de retorno automático al dashboard (retardo ≤ 3s).
6. **R6 — `emisor_desconectado` en el frontend:** los listeners ven un aviso visible ("El emisor se desconectó, la clase finalizará") y la sala se cierra tras el timeout del backend.
7. **R7 — Errores de WS visibles:** cualquier `{type:"error"}` recibido en la sala se muestra como banner con el `mensaje` del backend; no hay redirecciones silenciosas a dashboard (reemplaza `SalaView.jsx:160-162`).
8. **R8 — Error de micrófono denegado:** si `getUserMedia` falla, se muestra el mensaje "Permiso de micrófono denegado. Actívalo en la configuración del navegador e inténtalo de nuevo" y el botón vuelve al estado "Iniciar Transmisión".
9. **R9 — Sesión expirada:** cualquier respuesta 401 de la API (o error de token en WS) limpia `localStorage` y redirige a `#/login` con el mensaje "Sesión expirada, inicia sesión nuevamente".
10. **R10 — Estado en vivo en dashboard:** cada asignatura muestra punto verde "En vivo" o gris "Sin clase activa" según `GET /api/salas/{room_id}/estado`. El botón primario muestra "Entrar a la clase" si la sala está activa y "Iniciar Transmisión de Clase" si no. Se elimina el badge estático "Micrófono Conectado".
11. **R11 — Estados de carga/error en dashboard:** se distingue entre cargando, error de red (mensaje + botón reintentar) y lista vacía ("No tienes asignaturas inscritas"). Un error de red no muestra la lista vacía.
12. **R12 — Tiempo transcurrido:** durante la grabación, el emisor ve el tiempo transcurrido en mm:ss junto a los controles (el estado `tiempo` ya se calcula en `SalaView.jsx:108` pero no se muestra).
13. **R13 — Sin controles muertos:** los botones gear (Configuración), Expandir y Más opciones se eliminan de `SalaView` y `ClaseDetailView` (o se les da función real). El filtro de fecha del historial es funcional o desaparece del UI.
14. **R14 — Filtro de fecha funcional:** el filtro de fecha del historial filtra por mes (select con los meses que tienen clases, o bien "Este mes / Mes anterior / Todas"), y `filtroFecha` se aplica efectivamente al listado.
15. **R15 — Detalle de clase con error:** ante 404 u otro error, `ClaseDetailView` muestra "Clase no encontrada" con botón "Volver al historial"; el estado "Cargando..." solo se muestra mientras la petición está pendiente.
16. **R16 — Normalización de RUT:** el login acepta RUT con/sin puntos y guión, valida dígito verificador (mod-11) antes de enviar y lo envía normalizado; el error de credenciales se muestra claro y sin recargar la página.
17. **R17 — Tamaño de fuente persistente:** A+/A− se persiste en `localStorage` y se aplica al cargar en `SalaView` y `ClaseDetailView`.
18. **R18 — Accesibilidad:** todos los botones solo-icono tienen `aria-label`; los tabs del `Header` son `<button>` con estado `aria-current`; los errores y avisos visibles cumplen contraste sobre el tema oscuro.
19. **R19 — Auth en REST:** `GET /api/cursos`, `GET /api/cursos/{id}/glosario`, `GET /api/salas/{room_id}/estado`, `GET /api/historial` y `GET /api/historial/{clase_id}` requieren token válido (`Authorization: Bearer`); responden 401 con detalle claro si falta o es inválido. `/api/auth/login` y `/health` no requieren token.
20. **R20 — Autorización de detalle:** `GET /api/historial/{clase_id}` solo devuelve la clase si el RUT del token es el emisor o está inscrito en `[cod_ramo]-[seccion]` de la clase; en otro caso 403/404.
21. **R21 — Backend cierra listeners:** al finalizar la sala (explícito o timeout), el backend difunde `clase_finalizada` y cierra el WebSocket de cada listener; ningún listener queda conectado en silencio.
22. **R22 — Timeout de emisor:** si el emisor se desconecta sin acción `finalizar`, el backend difunde `{type:"emisor_desconectado"}`, espera `SALA_TIMEOUT_MS` (default 30000) y luego guarda el timeline parcial (finaliza la clase con `titulo` null) y difunde `clase_finalizada`.
23. **R23 — Limpieza de código huérfano:** se eliminan `Landing.jsx`, `ProfesorView.jsx`, `AlumnoView.jsx`, `CursoSelector.jsx`, `Subtitulos.jsx`, `EstadoConexion.jsx`, `ControlesEmisor.jsx`. `SenaPlayer.jsx` se mantiene y se mejora. No quedan componentes importados por ningún archivo del árbol de `App.jsx`.
24. **R24 — Verificación:** `ruff check backend`, `pytest backend/tests` y `pnpm --prefix frontend build` pasan sin errores ni warnings nuevos. Los tests existentes se actualizan a la nueva auth (token en header) y se agregan tests de los nuevos comportamientos de sala.

## 5. Diseño técnico

### 5.1 Frontend

```
frontend/src/
├── components/
│   ├── Feedback.jsx          # NUEVO: banner/toast (tipo: error|info|success, auto-ocultar)
│   ├── SenaPlayer.jsx        # MEJORADO: video autoplay/muted/loop + rótulo + onError fallback
│   ├── EstadoConexion.jsx    # NUEVO (reemplaza al huérfano): indicador conectado/reconectando/desconectado
│   ├── FinalizarModal.jsx    # sin cambios
│   └── Header.jsx            # tabs como <button> + aria-current
├── hooks/
│   └── useWebSocket.js       # MEJORADO: backoff 3/6/12/24s (máx 5), estado + intentos, reintento manual
├── api/
│   └── cliente.js            # MEJORADO: header Authorization, manejo central 401 → login, normalizarRut()
├── views/
│   ├── LoginView.jsx         # normalización/validación de RUT
│   ├── DashboardView.jsx     # estado en vivo por asignatura, botón dinámico, sin badge falso
│   ├── SalaView.jsx          # usa useWebSocket + EstadoConexion + SenaPlayer + Feedback + tiempo mm:ss
│   ├── HistorialView.jsx     # filtro de fecha funcional
│   └── ClaseDetailView.jsx   # error state + SenaPlayer en replay
└── App.css                   # estilos: feedback, indicador de estado, dot en vivo
```

**Feedback de errores (patrón):** cada vista de sala/dashboard maneja un estado `feedback {tipo, mensaje}` renderizado por `Feedback.jsx`; se auto-oculta a los 5s para `info/success` y persiste con botón de cierre para `error`.

**SalaView con `useWebSocket`:** la conexión manual (`SalaView.jsx:123-167`) se reemplaza por el hook mejorado con `rol`/`roomId` como URL estable; el callback `onMessage` centraliza: `segmento` (lógica existente + `SenaPlayer`), `clase_finalizada` (aviso + `setTimeout` a `#/dashboard`), `emisor_desconectado` (aviso), `error` (banner con `mensaje`).

**Tamaño de fuente persistente:**

```js
const [tamFuente, setTamFuente] = useState(() =>
  Number(localStorage.getItem('puente_lsch_font_size')) || 18
)
const cambiarTam = (delta) => setTamFuente((s) => {
  const nuevo = Math.min(32, Math.max(12, s + delta))
  localStorage.setItem('puente_lsch_font_size', String(nuevo))
  return nuevo
})
```

**Normalización de RUT (cliente):**

```js
export function normalizarRut(rut) {
  const limpio = (rut || '').replace(/[.\-\s]/g, '')
  if (!/^\d{7,8}[0-9kK]$/.test(limpio)) return null
  const cuerpo = limpio.slice(0, -1)
  const dv = limpio.slice(-1).toUpperCase()
  const suma = [...cuerpo].reverse().reduce((acc, d, i) => acc + Number(d) * (2 + (i % 6)), 0)
  const dvEsperado = 11 - (suma % 11)
  const dvCalculado = dvEsperado === 11 ? '0' : dvEsperado === 10 ? 'K' : String(dvEsperado)
  return dv === dvCalculado ? `${cuerpo}-${dv}` : null
}
```

### 5.2 Backend

**Cierre de listeners al finalizar (`main.py`, bloque emitter `finally`):**

```python
async def _cerrar_listeners(room_id: str, evento: dict) -> None:
    sala = await RoomManager.obtener(room_id)
    if not sala:
        return
    await RoomManager.broadcast(room_id, evento)
    for ws in list(sala.listeners):
        try:
            await ws.close()
        except Exception:
            pass
    sala.listeners.clear()
```

- Finalización explícita: tras `finalizar_clase(...)`, llamar `_cerrar_listeners(room_id, {"type": "clase_finalizada", "clase_id": ...})` y luego `RoomManager.eliminar(room_id)`.
- Desconexión sin finalizar (R22): `broadcast({"type": "emisor_desconectado"})` → `await asyncio.sleep(SALA_TIMEOUT_MS / 1000)` → `finalizar_clase(clase_id, fin, duracion, None)` → `_cerrar_listeners(...)` → `eliminar`. Usar `SALA_TIMEOUT_MS` de `get_settings()` (`core/config.py:17`).

**Loop de listener (reemplaza `main.py:219-226`):** escuchar solo el cierre del cliente:

```python
try:
    while True:
        msg = await ws.receive()
        if msg["type"] == "websocket.disconnect":
            break
except (WebSocketDisconnect, RuntimeError):
    pass
finally:
    await RoomManager.quitar_listener(room_id, ws)
```

**Auth en REST:** helper en `core/auth.py`:

```python
def obtener_rut(request: Request) -> str:
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token no proporcionado")
    rut = verificar_token(header[7:])
    if not rut:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")
    return rut
```

Aplicar en los endpoints de R19 (quitar el `rut: str = Query("")` de `api_cursos`, `api_historial`, `api_historial_detalle`, `api_sala_estado` y `usuario_me`). `api_historial_detalle` además valida inscripción/emisor (R20) usando `RoomManager`/consulta SQL.

**Tests a actualizar:** `test_auth.py`, `test_sala.py`, `test_historial.py` (enviar token en header en lugar de `?rut=`); nuevos casos: 401 sin token, 403 en detalle de clase ajena, listener desconectado tras `clase_finalizada`, timeline parcial tras `emisor_desconectado` + timeout (simular con `SALA_TIMEOUT_MS` pequeño o monkeypatch).

### 5.3 Flujos de usuario objetivo

- **Estudiante emisor:** dashboard → "Iniciar Transmisión de Clase" → permisos ok → tiempo mm:ss + estado "conectado" → recibe subtítulos y video de la seña → pausar/reanudar → "Finalizar y Guardar" (título) → dashboard.
- **Estudiante oyente:** dashboard (sala activa → "Entrar a la clase") → aviso de conexión → recibe subtítulos + video de señas → al finalizar el emisor: aviso "La clase terminó" → dashboard.
- **Recuperación:** se cae la red → "reconectando" visible → reintentos → si agota: mensaje con "Reintentar". Emisor desconectado: oyentes ven aviso y la clase se guarda parcialmente.

## 6. Criterios de aceptación

- [ ] R1–R24 satisfechos.
- [ ] Con `ASR_PROVIDER=stub`: el alumno emisor ve subtítulos + video de seña en el panel; un segundo dispositivo oyente recibe el broadcast y ve el video; al "Finalizar y Guardar" del emisor, el oyente ve el aviso y vuelve al dashboard.
- [ ] Con el emisor desconectado (cerrar pestaña): los oyentes ven "emisor desconectado" y, tras `SALA_TIMEOUT_MS`, la clase queda en el historial como parcial.
- [ ] Sin micrófono (permiso denegado): mensaje de error claro y el botón sigue disponible.
- [ ] Con token expirado/inválido: redirección a login con mensaje de sesión expirada (REST y WS).
- [ ] Login con RUT con/sin puntos y guión funciona; RUT con DV incorrecto se rechaza antes de enviar.
- [ ] El dashboard muestra "En vivo"/"Sin clase activa" por asignatura y no muestra el badge "Micrófono Conectado".
- [ ] No hay botones sin función en sala ni detalle; el filtro de fecha del historial filtra de verdad.
- [ ] Una clase inexistente en `#/historial/99999` muestra "Clase no encontrada" (no "Cargando..." infinito).
- [ ] A+/A− persiste entre sesiones.
- [ ] `ruff check backend`, `pytest backend/tests` y `pnpm --prefix frontend build` pasan.
- [ ] `docker compose up --build` levanta y el flujo end-to-end (stub) funciona: login → dashboard → iniciar → subtítulos + video → finalizar → historial → replay con video.

## 7. Tareas de implementación

1. **Backend — `core/auth.py`:** helper `obtener_rut(request)` (Bearer).
2. **Backend — endpoints:** migrar `api_cursos`, `usuario_me`, `api_sala_estado`, `api_historial`, `api_historial_detalle` a auth con token; autorización de detalle (R20).
3. **Backend — `main.py`:** `_cerrar_listeners`; aplicar en finalización explícita y en timeout de emisor (R21, R22); loop de listener simplificado.
4. **Backend — tests:** actualizar existentes + nuevos casos (R24).
5. **Frontend — `cliente.js`:** header `Authorization`, manejo central de 401, `normalizarRut()`.
6. **Frontend — `useWebSocket.js`:** backoff 3/6/12/24s (máx 5), estados e intentos.
7. **Frontend — componentes:** `Feedback.jsx`, `EstadoConexion.jsx` (nuevos), `SenaPlayer.jsx` (mejorado con fallback), `Header.jsx` (tabs como botones).
8. **Frontend — `SalaView.jsx`:** migrar a `useWebSocket`, indicador de conexión, banners de error, handler `clase_finalizada`/`emisor_desconectado`, `SenaPlayer`, tiempo mm:ss, quitar controles muertos, persistencia de fuente.
9. **Frontend — `LoginView.jsx`:** normalización/validación de RUT y mensajes.
10. **Frontend — `DashboardView.jsx`:** estado en vivo renderizado, botón dinámico, sin badge falso, estados carga/error.
11. **Frontend — `HistorialView.jsx`:** filtro de fecha funcional.
12. **Frontend — `ClaseDetailView.jsx`:** error state + `SenaPlayer` en replay + quitar controles muertos.
13. **Frontend — limpieza:** eliminar `Landing.jsx`, `ProfesorView.jsx`, `AlumnoView.jsx`, `CursoSelector.jsx`, `Subtitulos.jsx`, `EstadoConexion.jsx` (viejo), `ControlesEmisor.jsx` (R23).
14. **Frontend — `App.css`:** estilos de feedback, indicador de estado y dot en vivo.
15. **Verificación completa** (sección 8) + actualizar `docs/historial_implementacion.md` al commitear.

## 8. Verificación

```powershell
# Backend
cd backend
.\venv\Scripts\activate
python scripts\seed_glosario.py
pytest tests -v
ruff check .

# Frontend
cd frontend
pnpm build
pnpm dev
# flujo stub end-to-end:
#   login (RUT con puntos/guión) → dashboard → "Iniciar Transmisión de Clase"
#   → verificar: indicador conectado, mm:ss, subtítulos + video de seña
#   → segundo dispositivo/ventana: "Entrar a la clase" → recibe broadcast + video
#   → emisor: "Finalizar y Guardar" → oyente ve aviso y vuelve a dashboard
#   → cerrar pestaña del emisor en otra sesión: oyentes ven "emisor desconectado"
#   → historial: clase guardada → detalle → modo replay reproduce video de señas
#   → filtrar historial por fecha funciona
#   → `#/historial/99999` muestra "Clase no encontrada"
#   → denegar micrófono: error visible

# Docker
docker compose up --build
# mismo flujo en http://localhost:5173
```

## 9. Notas / decisiones diferidas

- **Filtro de fecha:** se implementa como select de meses disponibles (derivados del historial cargado), evitando un date picker; si resulta innecesario en la revisión, se elimina del UI (decisión abierta en implementación, siempre que no quede un control muerto).
- **Reintento manual:** al agotar los 5 reintentos de backoff, se ofrece "Reintentar" manual; no se implementa notificación push ni reconexión infinita.
- **Badge "EN VIVO":** queda condicionado a estado conectado; si se quiere distinguir "grabando" del emisor, se usa el indicador de tiempo mm:ss.
- **"Reclamar emisor"** y **catch-up** de listeners tardíos siguen diferidos (ver SPEC-004 §9).
- **Auth REST:** es una corrección de la desviación de SPEC-004 R10 (middleware de auth nunca se implementó; los endpoints usaban `?rut=`). No agrega SSO.
- **Contraste/estilos de los nuevos avisos:** se verificarán visualmente contra el tema oscuro existente; no se introduce una librería de componentes.
