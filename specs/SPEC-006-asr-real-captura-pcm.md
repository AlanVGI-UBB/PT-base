# SPEC-006 — Transcripción real: captura PCM en el navegador + faster-whisper local

**Etapa del plan:** Semestre 1 · Etapa 3 (prueba de concepto) y adelanto de Semestre 2 · Etapa 4 (backend robusto) de `docs/plan_desarrollo_tecnico.md`. Propuesta: actividad AP Obj. 2 Act. 1 ("Diseño preliminar del módulo de captura y streaming de audio (PoC)"). Informe: RF06, RF07, RF10, RF12, RN10, RNF11, RNF15, §2.5.1 y Tabla 4.1.
**Estado:** Borrador
**Depende de:** SPEC-004, SPEC-005

---

## 1. Objetivo

Que la sala transcriba la voz real que entra por el micrófono. Hoy la "transcripción" son 10 frases fijas que el stub repite sin mirar el audio. Esta spec reemplaza la captura `MediaRecorder` (WebM/Opus) por PCM 16 kHz, agrega un proveedor ASR local con faster-whisper y corrige el manejo de resultados provisionales y finales en el servidor.

## 2. Contexto y supuestos

- **Estado actual del ASR** (revisión del 2026-11-16):
  - `ASR_PROVIDER=stub` es el valor por defecto (`core/config.py:11`, `docker-compose.yml`). `asr/stub.py` ignora `audio_iter` y emite `FRASES` en bucle.
  - `asr/google_streaming.py` no funciona: `_request_gen` (línea 58) itera `_audio_chunks_sync`, una lista que solo llena `_collect_chunks` (línea 68), función que nunca se invoca. Solo se envía la configuración y ningún audio. Además usa la API v1 (`google.cloud.speech`), no la v2 que indica el plan, y `google-cloud-speech` no está instalado en `backend/venv`. Conclusión por lectura de código; no se ejecutó contra Google.
  - El emisor captura con `MediaRecorder` en trozos de 250 ms (`SalaView.jsx:164-176`). En WebM solo el primer trozo lleva la cabecera del contenedor: los siguientes no se pueden decodificar por separado y una reconexión deja el flujo sin cabecera.
  - `main.py:173-194` incrementa `segmento_idx`, ejecuta el matching y persiste un `evento_clase` por **cada** resultado, incluidos los provisionales. Con un ASR que entregue parciales esto duplicaría texto en el historial y dispararía clips repetidos (contradice RN10 del informe).
  - `ResultadoASR.inicio_ms` y `fin_ms` siempre valen 0.
- **Equipo de desarrollo verificado:** NVIDIA GeForce RTX 3050 Laptop de 6 GB, toolkit CUDA 12.4 y `ffmpeg` en el PATH; Python 3.14 en `backend/venv` (también hay 3.12 instalado).
- **Compatibilidad comprobada solo a nivel de resolución:** `pip install --dry-run faster-whisper` en el venv resuelve `faster-whisper 1.2.1`, `ctranslate2 4.9.0` y `av 19.0.2`. No se instaló ni se cargó un modelo. La inferencia en GPU requiere además las bibliotecas cuBLAS y cuDNN que exija esa versión de CTranslate2: se debe seguir la documentación de faster-whisper al instalar, no asumir que el toolkit CUDA basta.
- **Decisión de proveedor:** ASR local. Evita credenciales, costo por uso y el envío de voz a un tercero, que según §4.2.3 del informe requiere autorización antes de probar con personas. El ASR remoto sigue siendo un candidato a comparar en Proyecto de Título.
- **Formato de audio:** PCM lineal de 16 bits, mono, 16 kHz, que es la entrada nativa de Whisper y coincide con la estimación de §4.1.3 del informe (32 kB/s). Cumple la restricción de §3.2: el audio se normaliza al formato del motor.
- El audio sigue sin guardarse: solo existe en memoria mientras se transcribe.

## 3. Alcance

### Incluido

1. Captura PCM en el navegador con `AudioWorklet` y envío por el WebSocket existente.
2. Medidor de nivel de entrada y aviso de silencio sostenido.
3. Segmentador de audio en el servidor (ventanas provisionales y finales).
4. Proveedor `FasterWhisperProvider` seleccionable por configuración.
5. Corrección del handler de sala: identificador de segmento estable, matching y persistencia solo sobre texto final, vaciado del búfer al finalizar.
6. Retiro del proveedor de Google roto y de su dependencia.
7. Configuración, Docker y documentación de ejecución.

### Explícitamente fuera

- ASR remoto y comparación entre proveedores (Proyecto de Título).
- Inferencia con GPU dentro de Docker.
- Selector de dispositivo de entrada (RF06 parcial): se usa el micrófono predeterminado del sistema.
- Propagación de la pausa a los oyentes y permisos de captura (→ SPEC-009).
- Medición formal de WER y latencia (→ SPEC-008).
- Diarización, traducción y puntuación adicional a la que entrega el modelo.

## 4. Requisitos

1. **R1 — Contrato de audio:** el emisor envía mensajes binarios con PCM s16le mono 16 kHz en tramas de 1600 muestras (3200 bytes, 100 ms). El servidor descarta, con un `logger.warning` por sesión, toda trama de longitud impar o mayor que `ASR_MAX_TRAMA_BYTES` (por defecto 64000).
2. **R2 — Captura con AudioWorklet:** `SalaView` deja de usar `MediaRecorder`. La captura vive en `frontend/src/audio/` y entrega tramas según R1 aunque el `AudioContext` no quede a 16 kHz (remuestreo en el worklet). Al finalizar o salir se detienen las pistas del micrófono y se cierra el contexto.
3. **R3 — Nivel de entrada visible:** mientras se captura, el emisor ve un indicador del nivel de la señal. Si el nivel permanece bajo el umbral durante 10 s, aparece el aviso "No se detecta audio en el micrófono" sin detener la sesión; el aviso desaparece al volver la señal.
4. **R4 — Segmentación:** el servidor acumula el PCM y produce:
   - una ventana **final** cuando detecta `ASR_SILENCIO_MS` (600) de silencio tras voz, cuando el segmento alcanza `ASR_MAX_SEGMENTO_MS` (15000) o cuando no llegan tramas durante `ASR_SILENCIO_MS`;
   - una ventana **provisional** cada `ASR_PARCIAL_MS` (1000) mientras el segmento sigue abierto.
5. **R5 — Sin acumulación de retraso:** las ventanas finales siempre se transcriben. Si al terminar una inferencia hay más de `ASR_PARCIAL_MS` de audio pendiente, las provisionales se omiten hasta ponerse al día.
6. **R6 — Proveedor faster-whisper:** `ASR_PROVIDER=whisper` selecciona `FasterWhisperProvider`. El modelo se carga una sola vez por proceso (en el arranque si es el proveedor configurado), la inferencia corre fuera del bucle de eventos y dos salas simultáneas no ejecutan inferencias a la vez sobre el mismo modelo.
7. **R7 — Configuración del modelo:** `WHISPER_MODEL` (por defecto `small`), `WHISPER_DEVICE` (`auto` | `cuda` | `cpu`) y `WHISPER_COMPUTE_TYPE` (`auto`: `float16` en GPU, `int8` en CPU). Con `auto`, si la GPU no inicializa se usa CPU y se registra un `logger.warning` que lo dice.
8. **R8 — Silencio sin texto:** 30 s de silencio o ruido de fondo no producen ningún segmento. Se usa filtro de voz en la transcripción, no se condiciona al texto previo y se descartan resultados vacíos.
9. **R9 — Sesgo de vocabulario configurable:** con `ASR_PROMPT_GLOSARIO=true` (por defecto) el proveedor recibe los `texto_visible` del glosario de la sala como contexto inicial del modelo. Con `false` no se pasa contexto. La interfaz `StreamingASRProvider` acepta ese contexto como parámetro opcional y el stub lo ignora.
10. **R10 — Tiempos reales:** cada `ResultadoASR` lleva `segmento_id`, `inicio_ms` y `fin_ms` medidos en tiempo de audio desde el inicio de la sesión. Una ventana provisional y su final comparten `segmento_id`.
11. **R11 — Handler de sala:** un resultado provisional se difunde con `final: false` y no se persiste ni pasa por el matching. Un resultado final ejecuta el matching, persiste un único `evento_clase` y se difunde con `final: true`. El `segment_id` del evento es el `segmento_id` del ASR.
12. **R12 — Cliente por identificador:** `SalaView` reemplaza el subtítulo provisional por `segment_id` (no por "último no final") y nunca deja dos entradas con el mismo identificador.
13. **R13 — Vaciado al finalizar:** al recibir `{action: "finalizar"}` el servidor transcribe el audio pendiente, persiste y difunde ese último segmento y recién entonces emite `clase_finalizada`. Si el vaciado supera `ASR_FLUSH_TIMEOUT_MS` (5000) se abandona y se registra un `logger.warning`.
14. **R14 — Audio transitorio:** ningún módulo escribe audio en disco ni en la base de datos.
15. **R15 — Retiro de Google:** se eliminan `asr/google_streaming.py`, la rama `google` de `get_asr_provider`, `GOOGLE_APPLICATION_CREDENTIALS` y `google-cloud-speech` de `requirements.txt`. El mensaje de error de proveedor desconocido lista solo `whisper | stub`.
16. **R16 — Error de configuración claro:** con `ASR_PROVIDER=whisper` y el paquete o el modelo no disponibles, el arranque falla con un mensaje en español que indica qué instalar o cómo volver a `stub`.
17. **R17 — Docker:** la imagen del backend incluye faster-whisper. `docker-compose.yml` toma `ASR_PROVIDER`, `WHISPER_MODEL` y `WHISPER_DEVICE` del entorno (por defecto `stub`, `base` y `cpu`) y monta un volumen para la caché de modelos. El upstream de nginx es configurable con `BACKEND_UPSTREAM` (por defecto `backend:8000`) para poder apuntar el frontend en contenedor a un backend nativo con GPU.
18. **R18 — Tests:** se agregan pruebas del segmentador con PCM sintético y un transcriptor falso (sin cargar modelos), del handler con un proveedor falso que entrega provisional y final, y del rechazo de tramas fuera de contrato. Las 29 pruebas actuales siguen pasando. Una prueba de humo con el modelo real queda marcada `@pytest.mark.modelo` y no corre por defecto.
19. **R19 — Verificación mínima:** `ruff check backend`, `pytest backend/tests` y `pnpm --prefix frontend build` pasan sin errores.

## 5. Diseño técnico

### 5.1 Archivos

```
backend/app/asr/
├── base.py              # ResultadoASR con segmento_id; factory sin 'google'; contexto opcional
├── stub.py              # se mantiene para desarrollo y tests; adopta segmento_id
├── segmentador.py       # NUEVO: búfer PCM + detección de voz → ventanas
├── whisper_local.py     # NUEVO: FasterWhisperProvider
└── google_streaming.py  # ELIMINADO
backend/tests/
├── test_segmentador.py  # NUEVO
└── test_sala.py         # casos provisional/final, vaciado y tramas inválidas
frontend/src/audio/      # NUEVO directorio
├── pcm-worklet.js       # AudioWorkletProcessor: Float32 → Int16 a 16 kHz + nivel RMS
└── capturaPcm.js        # iniciar / pausar / reanudar / detener; callbacks onTrama y onNivel
```

`frontend/src/audio/` es un directorio nuevo. Se justifica porque la captura deja de ser unas líneas dentro de `SalaView` y pasa a ser un módulo con un worklet, que debe vivir en un archivo propio para que Vite lo empaquete como recurso (`new URL('./pcm-worklet.js', import.meta.url)`).

### 5.2 Contrato del proveedor

```python
@dataclass
class ResultadoASR:
    segmento_id: int
    texto: str
    estable: bool      # True = final
    inicio_ms: int     # tiempo de audio desde el inicio de la sesión
    fin_ms: int

class StreamingASRProvider(Protocol):
    def transcribe_stream(
        self,
        audio_iter: AsyncIterator[bytes],
        lang: str = "es",
        contexto: list[str] | None = None,
    ) -> AsyncIterator[ResultadoASR]: ...
```

### 5.3 Segmentador

```python
@dataclass
class Ventana:
    segmento_id: int
    pcm: np.ndarray   # float32 mono 16 kHz
    inicio_ms: int
    fin_ms: int
    final: bool

class Segmentador:
    def alimentar(self, trama: bytes) -> list[Ventana]: ...
    def cerrar(self) -> Ventana | None: ...   # vaciado al finalizar o por falta de tramas
```

La detección de voz del segmentador es por energía (RMS en subtramas de 30 ms, umbral y tiempo de cola configurables). Es determinista y se puede probar sin modelo. El filtro de voz del propio faster-whisper se activa además en la transcripción para limpiar los bordes. `numpy` ya es dependencia transitiva de spaCy; se declara explícita en `requirements.txt`.

### 5.4 Proveedor

- Modelo único por proceso, creado con `WhisperModel(modelo, device=..., compute_type=...)` y protegido por un `asyncio.Lock`.
- Cada ventana se transcribe con `asyncio.to_thread`, idioma `es`, filtro de voz activado y sin condicionar al texto previo. El contexto de R9 se pasa como texto inicial.
- El bucle consume `audio_iter`, alimenta el segmentador y emite un `ResultadoASR` por ventana con texto no vacío. Al terminar `audio_iter` llama a `cerrar()`.

### 5.5 Handler de sala (`main.py`)

- `_receiver` valida la trama (R1) antes de encolarla. Al recibir `finalizar` encola un centinela `None` en lugar de cancelar la transcripción.
- `_audio_gen` termina al leer el centinela; el proveedor vacía su búfer y `_transcribir` termina solo. El cierre espera esa tarea hasta `ASR_FLUSH_TIMEOUT_MS`.
- `_transcribir` aplica R11:

```python
async for r in provider.transcribe_stream(_audio_gen(), contexto=contexto):
    if not r.texto.strip():
        continue
    ts_ms = int(time.time() * 1000) - t_inicio
    senas = buscar_terminos(r.texto, sala.glosario_por_lema) if r.estable else []
    if r.estable:
        guardar_evento(clase_id_db, ts_ms, r.texto, True, json.dumps(senas, ensure_ascii=False))
    await RoomManager.broadcast(room_id, {
        "type": "segmento", "segment_id": r.segmento_id, "texto": r.texto,
        "final": r.estable, "senas": senas, "timestamp_ms": ts_ms,
    })
```

### 5.6 Captura en el cliente

- `capturaPcm.iniciar({ onTrama, onNivel })` pide `getUserMedia({ audio: { channelCount: 1 } })`, crea el `AudioContext`, registra el worklet y conecta `MediaStreamSource → AudioWorkletNode`.
- El worklet acumula muestras, remuestrea a 16 kHz si `sampleRate` es otro, convierte a `Int16` y publica tramas de 1600 muestras junto con el RMS de cada una.
- `SalaView` envía cada trama con `ws.send(buffer)` solo si el socket está abierto. Pausar deja de enviar tramas (la propagación a oyentes es de SPEC-009).
- `AudioWorklet` exige contexto seguro: funciona en `localhost` y en el HTTPS que ya entrega nginx.

### 5.7 Variables de configuración nuevas

| Variable | Por defecto | Uso |
|---|---|---|
| `ASR_PROVIDER` | `stub` | `whisper` \| `stub` |
| `WHISPER_MODEL` | `small` | tamaño del modelo |
| `WHISPER_DEVICE` | `auto` | `auto` \| `cuda` \| `cpu` |
| `WHISPER_COMPUTE_TYPE` | `auto` | precisión numérica |
| `ASR_SILENCIO_MS` | `600` | silencio que cierra un segmento |
| `ASR_MAX_SEGMENTO_MS` | `15000` | duración máxima de un segmento |
| `ASR_PARCIAL_MS` | `1000` | cadencia de provisionales |
| `ASR_FLUSH_TIMEOUT_MS` | `5000` | espera del vaciado final |
| `ASR_MAX_TRAMA_BYTES` | `64000` | límite por mensaje binario |
| `ASR_PROMPT_GLOSARIO` | `true` | contexto de vocabulario |

## 6. Criterios de aceptación

- [ ] R1–R19 satisfechos.
- [ ] Con `ASR_PROVIDER=whisper`, al decir una frase al micrófono aparece texto provisional que se va corrigiendo y, tras una pausa al hablar, queda una sola línea final con lo dicho.
- [ ] Una frase que contiene un término del glosario muestra el clip una sola vez, al consolidarse el texto.
- [ ] 30 s sin hablar no agregan subtítulos.
- [ ] Al pulsar "Finalizar y Guardar" a mitad de frase, esa frase queda en el historial.
- [ ] Un segundo dispositivo oyente recibe los mismos `segment_id` y el mismo texto final.
- [ ] El historial de la clase contiene una fila por segmento final y ninguna provisional.
- [ ] Con `ASR_PROVIDER=stub` el flujo se comporta como antes de esta spec.
- [ ] No existe ningún archivo de audio generado por la aplicación.
- [ ] `docker compose up --build` levanta con los valores por defecto.

## 7. Tareas de implementación

0. **Previo:** confirmar en un commit propio, con su entrada en `docs/historial_implementacion.md`, los cambios que hoy están sin commitear (túnel de Cloudflare, RUT de prueba con dígito verificador válido, WebSocket en el mismo origen, `run.ps1`, `run-cloudflare.ps1`).
1. Instalar `faster-whisper` en `backend/venv` y cargar un modelo. Si la instalación o la carga fallan en Python 3.14, recrear el venv con Python 3.12 y dejarlo anotado en el README.
2. `asr/base.py`: contrato nuevo, retiro de `google`.
3. `asr/segmentador.py` + `tests/test_segmentador.py`.
4. `asr/whisper_local.py`; adaptar `asr/stub.py` al contrato.
5. `core/config.py` y `.env.example`: variables de §5.7; retiro de `GOOGLE_APPLICATION_CREDENTIALS`.
6. `main.py`: validación de tramas, centinela de fin, R11 y R13; carga del modelo en `lifespan`.
7. `frontend/src/audio/`: worklet y módulo de captura.
8. `SalaView.jsx`: integrar la captura, el indicador de nivel, el aviso de silencio y el reemplazo por `segment_id`.
9. `requirements.txt`, `backend/Dockerfile`, `docker-compose.yml`, `frontend/nginx.conf` (R17).
10. Tests de sala (R18).
11. Verificación de §8 y entrada en `docs/historial_implementacion.md`.

## 8. Verificación

```powershell
ruff check backend
pytest backend/tests
pnpm --prefix frontend build

# Flujo real, backend nativo con GPU
cd backend
.\venv\Scripts\activate
$env:ASR_PROVIDER = "whisper"
python scripts\seed_glosario.py
uvicorn app.main:app --port 8000
# en otra terminal
cd frontend
pnpm dev
# Navegador en http://localhost:5173:
#   login → dashboard → "Iniciar Transmisión" → hablar
#   → provisional que se corrige → línea final → clip si hay término
#   → guardar silencio 30 s: no aparece texto
#   → "Finalizar y Guardar" a mitad de frase → la frase está en el historial
#   → segunda ventana como oyente: mismos segmentos

# Prueba de humo con modelo real (opcional)
pytest backend/tests -m modelo
```

## 9. Notas / decisiones diferidas

- **Proveedor de Google:** se retira en vez de repararlo porque no hay credenciales para probarlo y enviar voz a un tercero requiere una autorización que aún no existe. La abstracción `StreamingASRProvider` se mantiene para incorporar un proveedor remoto en Proyecto de Título. Si se prefiere repararlo ahora, es un cambio de alcance de esta spec.
- **Detección de voz por energía:** es la línea base. Si en aula con ruido corta mal los segmentos, se reemplaza por un detector basado en modelo sin cambiar la interfaz del segmentador.
- **Modelo por defecto `small`:** es un punto de partida, no una selección. La elección entre tamaños y entre GPU y CPU se decide con las mediciones de SPEC-008.
- **GPU en Docker:** diferido. Para demostraciones con GPU se ejecuta el backend nativo y, si se necesita HTTPS para otros dispositivos, se apunta nginx al host con `BACKEND_UPSTREAM`.
- **Selector de micrófono** (RF06 completo) y **reconexión del emisor a la misma clase** (RF20) quedan para Proyecto de Título.
