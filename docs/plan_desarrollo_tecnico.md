# Plan de desarrollo técnico
## Plataforma de inclusión de estudiantes sordos — LSCh

Este documento es el complemento técnico de la propuesta formal: aquí se detalla **qué construir, en qué orden, con qué tecnología y cómo**, para que puedas empezar a programar sin quedarte pegado en decisiones de stack.

Principio rector para todo el proyecto: **construir el flujo profesor → alumno primero, completo y evaluado, antes de tocar el módulo secundario**. Todo lo que sigue está ordenado bajo esa premisa.

---

## 1. Arquitectura y decisiones de stack

| Componente | Tecnología recomendada | Alternativa | Por qué |
|---|---|---|---|
| Backend / orquestador | **Python 3.11 + FastAPI** | Node.js + Express | Ecosistema ML/audio/visión (faster-whisper, MediaPipe, PyTorch) vive en Python; FastAPI da WebSockets nativos, async, y documentación OpenAPI automática (útil para la memoria) |
| Transcripción de voz (ASR) | **Google Cloud Speech-to-Text v2 (streaming, es-CL)** | Web Speech API (prototipo rápido) / faster-whisper local (si hay GPU) | Streaming real, soporte de español chileno, capa gratuita de 60 min/mes; ver sección 3 para cuándo usar cada alternativa |
| Coincidencia texto→seña | **spaCy (`es_core_news_md`)** para lematización + diccionario propio | Matching exacto por string (más simple, menos robusto) | Necesitas reconocer "hablando", "habló", "hablar" como el mismo término del glosario |
| Base de datos del glosario | **SQLite** | PostgreSQL | 80–150 términos no justifican un motor pesado; migras a Postgres solo si escalas a múltiples cursos en paralelo |
| Videos de señas | Archivos MP4 servidos como estáticos desde el propio backend | Bucket cloud (S3/GCS) | Volumen pequeño (decenas de clips cortos), no necesitas infraestructura extra |
| Transporte en tiempo real | **WebSockets** (nativos en FastAPI) | Polling HTTP | Latencia; polling se siente "atrasado" en clase |
| Cliente del alumno y del profesor | **Progressive Web App (PWA)**, React + Vite | App nativa (Android/iOS) | Un solo código corre en tablet, laptop o celular sin pasar por tiendas de apps — resuelve tu duda de hardware sin comprometerte a un dispositivo específico |
| Captura de audio del profesor | `getUserMedia` + `MediaRecorder` en la misma PWA (rol "profesor") | App nativa dedicada | El micrófono lavalier (por cable o Bluetooth) se conecta al teléfono/laptop como entrada de audio estándar; el software no necesita saber qué micrófono es |
| Extracción de puntos clave (módulo secundario) | **MediaPipe Tasks Vision** (`HandLandmarker` + `PoseLandmarker`), corriendo **en el navegador** vía `@mediapipe/tasks-vision` | Procesar el video en el backend | Corriendo en el cliente evitas mandar video crudo del alumno al servidor — solo viajan coordenadas numéricas; más rápido y más respetuoso de la privacidad |
| Clasificador de señas (módulo secundario) | **DTW (Dynamic Time Warping) + k-NN** sobre las secuencias de puntos clave | Red neuronal pequeña (1D-CNN o LSTM) como mejora futura | Con datasets chicos (30–50 repeticiones por seña), DTW es robusto, no requiere entrenamiento pesado, y es defendible metodológicamente: es la línea base correcta antes de saltar a deep learning |
| Síntesis de voz (texto→voz para el profesor) | Web Speech API (`SpeechSynthesis`, nativo del navegador) | Google Cloud Text-to-Speech | Gratis, sin backend adicional; solo pasas a Cloud TTS si la voz del navegador suena demasiado robótica |
| Despliegue | **Docker Compose** sobre el hardware que defina la universidad | Cloud (AWS/GCP) | Portabilidad: mismo contenedor corre en un PC de laboratorio, un mini-servidor o tu laptop durante el piloto |
| Control de versiones | Git + GitHub (o GitLab institucional) | — | — |

---

## 2. Estructura del repositorio

```
proyecto-titulo/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, endpoints y websockets
│   │   ├── asr/                 # módulo de transcripción
│   │   ├── glossary/            # modelo de datos + matching engine
│   │   ├── signs_recognition/   # módulo secundario (DTW, clasificador)
│   │   └── evaluation/          # logging de métricas (WER, latencia)
│   ├── data/
│   │   ├── glosario.db          # SQLite
│   │   └── videos_senas/        # clips MP4 del banco de señas
│   └── requirements.txt
├── frontend/                    # PWA (React + Vite)
│   ├── src/
│   │   ├── views/ProfesorView.jsx
│   │   ├── views/AlumnoView.jsx
│   │   └── lib/mediapipe.js
│   └── package.json
├── ml/                          # scripts de entrenamiento/experimentación,
│   │                           # separados del código de servicio
│   ├── grabar_dataset.py
│   ├── entrenar_clasificador.py
│   └── evaluar_wer.py
├── docs/                        # glosario validado, actas de reuniones con
│   │                            # la comunidad sorda, resultados de evaluación
└── docker-compose.yml
```

---

## 3. Plan paso a paso

### Semestre 1 — Anteproyecto

#### Etapa 1 (mes 1): Setup + estado del arte + contacto con comunidad sorda
No hay código todavía, pero sí configuración:
- Crea el repo con la estructura de arriba.
- Levanta un "hola mundo" de FastAPI con un endpoint WebSocket de eco (mandas texto, te lo regresa) — esto valida que el entorno de desarrollo funciona antes de meterle complejidad.
- En paralelo: gestiona el contacto con la persona sorda o intérprete (esto no es tarea de software, pero bloquea la etapa 2, así que táchala primero).

**Criterio de éxito de la etapa:** repo funcionando + colaboración confirmada.

#### Etapa 2 (mes 2): Glosario validado + diseño técnico
- Diseña el esquema SQLite:
  ```sql
  CREATE TABLE curso (id INTEGER PRIMARY KEY, nombre TEXT);
  CREATE TABLE termino (
    id INTEGER PRIMARY KEY,
    curso_id INTEGER REFERENCES curso(id),
    lema TEXT NOT NULL,          -- forma canónica ("derivada")
    texto_visible TEXT NOT NULL, -- lo que se muestra en pantalla
    video_url TEXT NOT NULL,
    n_palabras INTEGER DEFAULT 1 -- para saber si buscar como n-grama
  );
  ```
- Junto a tu colaborador/a sorda, define los 80–150 términos del curso piloto y agenda las sesiones de grabación de video (clips cortos, fondo neutro, misma persona para consistencia).
- Deja el diseño de arquitectura documentado (puedes reusar el diagrama ya generado).

**Criterio de éxito:** glosario validado en CSV/SQLite, calendario de grabación agendado.

#### Etapa 3 (mes 3): Prueba de concepto acotada
Aquí construyes la primera versión "de juguete" que demuestra el flujo completo con 10-15 términos:

1. **Transcripción rápida (para la PoC, no para el MVP final):** usa el **Web Speech API** del navegador directamente en el frontend — cero backend de ASR necesario todavía:
   ```javascript
   const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
   recognition.lang = 'es-CL';
   recognition.continuous = true;
   recognition.interimResults = true;
   recognition.onresult = (event) => {
     const texto = event.results[event.results.length - 1][0].transcript;
     enviarPorWebSocket(texto); // al backend, para hacer el matching
   };
   recognition.start();
   ```
   Nota: solo funciona bien en navegadores basados en Chromium. Es la opción correcta *solo* para esta prueba de concepto rápida, no para el sistema final (ver etapa 4).

2. **Motor de coincidencia (versión simple):** matching por substring sobre los 10-15 términos, sin lematización todavía.

3. **Despliegue en el cliente del alumno:** un WebSocket que recibe `{texto, video_url | null}` y muestra el subtítulo + reproduce el video si hay coincidencia.

**Criterio de éxito:** demo end-to-end funcionando con vocabulario chico, aunque sea frágil.

---

### Semestre 2 — Desarrollo

#### Etapa 4 (mes 1): Backend robusto + banco de señas completo
- **Migra la transcripción a Google Cloud Speech-to-Text (streaming v2, `es-CL`):**
  - Crea cuenta de Google Cloud (revisa si tu universidad tiene créditos educacionales — muchas facultades de informática los ofrecen).
  - El flujo es: audio del profesor (capturado con `MediaRecorder` en chunks de ~250ms, códec Opus/WebM) → WebSocket al backend → backend reenvía el stream a la API de Google → resultados parciales y finales vuelven por el mismo WebSocket hacia el cliente del alumno.
  - Como respaldo si el costo o la dependencia de internet es un problema: evalúa **faster-whisper** corriendo localmente con el patrón `whisper_streaming` (ventana deslizante + política de "acuerdo local"), que logra latencias de 1-3 segundos en GPU modesta. Es más trabajo de infraestructura, pero elimina el costo recurrente y la dependencia de conexión externa — vale la pena si consigues acceso a una GPU del laboratorio.
- **Motor de coincidencia con spaCy:**
  ```python
  import spacy
  nlp = spacy.load("es_core_news_md")

  def buscar_terminos(texto, glosario_por_lema, max_ngrama=3):
      doc = nlp(texto)
      lemas = [token.lemma_.lower() for token in doc]
      encontrados = []
      i = 0
      while i < len(lemas):
          match = None
          for n in range(max_ngrama, 0, -1):
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
  (Empieza probando n-gramas más largos para capturar términos compuestos como "raíz cuadrada" antes de caer a palabra suelta.)
- **Grabación del banco de señas completo:** con tu colaborador/a, graba los clips restantes hasta completar el glosario. Estándar recomendado: 1080p, fondo neutro, 3-5 segundos por clip, mismo encuadre para todos.

**Criterio de éxito:** backend transcribe + hace matching + sirve videos, con el glosario completo.

#### Etapa 5 (mes 2): Interfaz del alumno + integración
- Construye la PWA con React + Vite (`vite-plugin-pwa` para el manifest y service worker).
- Vista del alumno: subtítulos en vivo (texto que llega por WebSocket) + panel lateral o superpuesto con el video de la seña cuando hay coincidencia. Sincroniza para que el video no tape el subtítulo.
- Vista del profesor: pantalla simple con botón "iniciar/detener transcripción" y indicador de que el audio se está capturando.
- Prueba en al menos 3 dispositivos distintos (celular, tablet si consigues una, laptop) para confirmar que el enfoque PWA realmente resuelve la ambigüedad de hardware.

**Criterio de éxito:** MVP integrado, corriendo de punta a punta en red local.

#### Etapa 6 (mes 3): Piloto de evaluación
- Instrumenta el logging desde ya (no lo dejes para el final):
  - Cada segmento transcrito + timestamp de cuándo el profesor empezó a hablar y cuándo el alumno lo vio en pantalla → esto te da la **latencia end-to-end**.
  - Guarda la transcripción completa de la sesión piloto para compararla después contra una transcripción manual y calcular **WER** (Word Error Rate) con la librería `jiwer`:
    ```python
    from jiwer import wer
    error = wer(transcripcion_manual, transcripcion_del_sistema)
    ```
  - Aplica el cuestionario **SUS** (System Usability Scale, 10 preguntas estándar) a los estudiantes sordos que participen del piloto.
- Corre el piloto en una clase real (o simulada si no consigues una clase real a tiempo) y ajusta según lo que falle.

**Criterio de éxito:** métricas cuantitativas (WER, latencia) + cualitativas (SUS, entrevistas) documentadas para la memoria.

#### Etapa 7 (mes 4, si el tiempo alcanza): Módulo secundario alumno → profesor
Solo si las etapas 1-6 están sólidas. Es preferible entregar el núcleo pulido que dos mitades.

1. **Captura y extracción de puntos clave (en el navegador, sin backend):**
   ```javascript
   import { HandLandmarker, FilesetResolver } from "@mediapipe/tasks-vision";

   const vision = await FilesetResolver.forVisionTasks(
     "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision/wasm"
   );
   const handLandmarker = await HandLandmarker.createFromOptions(vision, {
     baseOptions: { modelAssetPath: "hand_landmarker.task" },
     numHands: 2,
     runningMode: "VIDEO",
   });
   // en cada frame: const resultado = handLandmarker.detectForVideo(video, timestamp);
   // resultado.landmarks -> array de 21 puntos por mano, listo para mandar al backend
   ```
2. **Recolección del dataset propio:** 10-15 frases fijas + alfabeto dactilológico, 30-50 repeticiones cada una, idealmente grabadas por tu colaborador/a sorda (no por ti imitando). Guarda cada repetición como una secuencia de landmarks (no como video), normalizada respecto a un punto de referencia (ej. el centro de los hombros) para que sea invariante a la posición frente a la cámara.
3. **Clasificador DTW + k-NN (línea base):**
   ```python
   from dtaidistance import dtw
   import numpy as np

   def clasificar(secuencia_nueva, plantillas):
       # plantillas: dict {nombre_seña: [lista de secuencias de ejemplo]}
       mejor_seña, mejor_distancia = None, float("inf")
       for seña, ejemplos in plantillas.items():
           for ejemplo in ejemplos:
               d = dtw.distance(secuencia_nueva.flatten(), ejemplo.flatten())
               if d < mejor_distancia:
                   mejor_distancia, mejor_seña = d, seña
       return mejor_seña, mejor_distancia
   ```
   Si con este baseline la exactitud es insuficiente y te queda tiempo, migra a una red pequeña (1D-CNN o GRU) entrenada con el mismo dataset — pero no partas por ahí.
4. **Salida:** texto mostrado en la vista del profesor + `speechSynthesis.speak(texto)` para voz.

**Criterio de éxito:** reconocimiento funcional de al menos el vocabulario acotado definido, con su propia métrica de exactitud reportada honestamente (aunque sea 70-80%, es un resultado válido de investigación si está bien medido).

---

## 4. Riesgos técnicos específicos y salidas de emergencia

| Si esto falla... | Haz esto |
|---|---|
| Google Cloud Speech-to-Text se pasa de presupuesto o no hay internet estable en la sala | Cae a Web Speech API (gratis, ya la tienes de la PoC) o a faster-whisper local si tienes GPU |
| El matching por lemas falla mucho con jerga/muletillas del profesor | Agrega una lista de sinónimos manual por término del glosario, no dependas solo del lematizador |
| El reconocimiento de señas (etapa 7) no llega a un nivel decente en el tiempo que queda | Redúcelo a solo alfabeto dactilológico (mucho más fácil de clasificar que frases completas) o déjalo como trabajo futuro bien documentado — no es una falla del proyecto |
| La latencia end-to-end se siente "atrasada" en clase real | Verifica primero si el cuello de botella es la red (usa red local, no wifi institucional saturado) antes de optimizar código |

---

## 5. Documentación oficial que vas a necesitar

- FastAPI WebSockets: fastapi.tiangolo.com/advanced/websockets
- Google Cloud Speech-to-Text streaming: cloud.google.com/speech-to-text/docs/streaming-recognize
- MediaPipe Tasks Vision (Hand/Pose Landmarker, web): ai.google.dev/edge/mediapipe/solutions/vision
- spaCy modelos en español: spacy.io/models/es
- jiwer (cálculo de WER): github.com/jitsi/jiwer
- dtaidistance (DTW): dtaidistance.readthedocs.io

---

*Complementa este plan con la propuesta formal (Word) ya generada. Ese documento explica el "qué" y el "por qué" ante el comité; este explica el "cómo" para tu propio proceso de desarrollo.*
