# Resultados de la Prueba de Concepto (PoC) — `SPEC-008`

Este documento consolida la evidencia cuantitativa reproducible de la PoC de **Puente LSCh** frente a las metas preliminares del informe (`RNF01`, `RNF03`, `RNF04`, `RNF06`), junto con sus condiciones experimentales, trazabilidad a los JSON de `ml/resultados/` y limitaciones explícitas.

> **Declaración de alcance y corpus:** las mediciones de transcripción automática se realizaron exclusivamente con grabaciones de lectura del propio autor (sin participantes externos ni docentes, sin evaluación de usabilidad/comprensión con usuarios sordos y sin validación lingüística de PIESDI). Toda cifra aquí citada proviene directamente de archivos JSON versionados en `ml/resultados/`.

---

## 1. Condiciones de medición

### Equipo y versiones de software
- **Sistema operativo:** `Windows-11-10.0.26300-SP0` (ejecución nativa del backend y scripts en `Python 3.14.0`, sin Docker).
- **CPU y RAM:** `Intel64 Family 6 Model 151 Stepping 2, GenuineIntel` (`8` núcleos físicos, `12` lógicos), `7967.9 MB` RAM.
- **GPU:** `NVIDIA GeForce RTX 3050 6GB Laptop GPU` (`6144 MB` VRAM, driver `610.47`).
- **Bibliotecas principales:** `faster-whisper==1.2.1`, `ctranslate2==4.9.0`, `onnxruntime==1.32.0`, `spacy==3.8.13` (`es_core_news_md==3.8.0`), `jiwer==4.0.0`, `psutil==7.2.2`, `websockets==16.1.1`, `fastapi==0.111.1`, `uvicorn==0.30.6`, `numpy==2.5.1`.

### Corpus de audio y transcripciones de referencia (`R9–R10`)
- **`ml/datos/audio/clase_01_cerca.wav`** (`404.65 s` = `6 min 44.65 s`, `982` palabras, `57` menciones de conceptos del glosario en la referencia): lectura del guion `ml/datos/guiones/clase_01.txt` en 10 tramos `.m4a` (`AAC 48 kHz 2 ch`) ensamblados a WAV PCM mono `16 bits / 16 000 Hz`, grabada con micrófono de teléfono móvil en condición cercana y silenciosa (`RMS p10 = 0.00334`, `p50 = 0.09471`).
- **`ml/datos/audio/clase_02_cerca.wav`** (`414.21 s` = `6 min 54.21 s`, `899` palabras, `70` menciones de conceptos del glosario en la referencia): lectura del guion `ml/datos/guiones/clase_02.txt` en 16 tramos `.m4a` ensamblados a WAV PCM mono `16 bits / 16 000 Hz`, también grabada con el teléfono en condición cercana y silenciosa (`RMS p10 = 0.00254`, `p50 = 0.09080`).
- **Normalización fija (`R6`):** todas las configuraciones aplican `ml/normalizacion.py` (Unicode NFC, minúsculas, signos de puntuación reemplazados por espacio y espacios colapsados; números tal como se transcriben, conservando tildes en español).
- **Definición de latencia del servidor (`R2`):** `latencia_servidor_ms = emitido_ms − llegada_fin_ms` medida con reloj monotónico dentro del mismo proceso, usando exactamente `Segmentador` (`silencio_ms=600`, `max_segmento_ms=15000`, `parcial_ms=1000`, tramas de `100 ms`) y `FasterWhisperProvider`. **Excluye explícitamente** la trama de captura en cliente (`100 ms`), el transporte por red y el renderizado en el dispositivo receptor.

### Trazabilidad de ejecuciones (`R16–R17`)

| Archivo en `ml/resultados/` | Tipo | Commit | Estado árbol | Alcance |
|---|---|---|---|---|
| `matching_ajuste_20261121_005927.json` | Matching | `0a8209c` | limpio | `36` frases partición `"ajuste"` |
| `matching_prueba_20261121_005931.json` | Matching | `0a8209c` | dirty* | `66` frases partición protegida `"prueba"` |
| `asr_clase_01_cerca_small_cuda_prompt_20261121_010621.json` | ASR (`1x`) | `0a8209c` | dirty* | `small`, CUDA, con prompt, Audio 1 |
| `asr_clase_02_cerca_small_cuda_prompt_20261121_011321.json` | ASR (`1x`) | `0a8209c` | dirty* | `small`, CUDA, con prompt, Audio 2 |
| `asr_clase_01_cerca_small_cuda_sinprompt_20261121_011350.json` | ASR (`--rapido`) | `0a8209c` | dirty* | `small`, CUDA, sin prompt, Audio 1 |
| `asr_clase_02_cerca_small_cuda_sinprompt_20261121_011418.json` | ASR (`--rapido`) | `0a8209c` | dirty* | `small`, CUDA, sin prompt, Audio 2 |
| `asr_clase_01_cerca_base_cpu_prompt_20261121_012108.json` | ASR (`1x`) | `0a8209c` | dirty* | `base`, CPU, con prompt, Audio 1 |
| `asr_clase_02_cerca_base_cpu_prompt_20261121_012807.json` | ASR (`1x`) | `0a8209c` | dirty* | `base`, CPU, con prompt, Audio 2 |
| `carga_escenario_A_stub_20261119_212452.json` | Carga | `4783e1b` | dirty† | Escenario A (`1 + 20`, `302.81 s`), `stub` |
| `carga_escenario_B_stub_20261119_212954.json` | Carga | `4783e1b` | dirty† | Escenario B (`2 × (1 + 10)`, `300.16 s`), `stub` |

*\* `dirty` debido únicamente a los propios JSON recién escritos en `ml/resultados/` durante la secuencia sobre el código de `0a8209c`.*  
*† Ejecutados sobre los cambios de instrumentación de `SPEC-008` antes del commit `0a8209c` (código de servidor WebSocket en `main.py`, `manager.py` y `stub.py` idéntico al consolidado en `0a8209c`).*

---

## 2. Transcripción automática (ASR) frente a `RNF03` y `RNF01`

Metas preliminares de referencia: **`RNF03` (`WER ≤ 25 %`)** y **`RNF01` (`p95 ≤ 5000 ms`, evaluado aquí solo en el tramo de servidor)**.

### Audio 1 — `clase_01_cerca.wav` (`404.65 s`, `982` palabras, `57` menciones de glosario, `58` segmentos finales)

| Configuración | Ritmo | WER (`S / D / I / N`) | Glosario recuperado | RTF total (c/ prov.) / finales | Latencia servidor (med / p95 / máx ms) | Mem. proc. / Δ GPU | Meta `RNF03` / `RNF01` srv |
|---|---|---|---|---|---|---|---|
| **`small` · CUDA · prompt=Sí** | `1x` real | **3.16 %** (`19 / 2 / 10 / 982`) | **57 / 57 (`100.0 %`)** | `0.3069` / `0.0449` (`344` prov.) | `414.0` / **`804.55`** / `3595.0` | `1050.89 MB` / `+107 MB` | Cumple / Cumple |
| `small` · CUDA · prompt=No | `--rapido` | 3.97 % (`27 / 2 / 10 / 982`) | 54 / 57 (`94.74 %`) | — / `0.0436` (`0` prov.) | n/a (`--rapido`) | `1177.49 MB` / `+82 MB` | Cumple / n/a |
| `base` · CPU · prompt=Sí | `1x` real | 8.25 % (`60 / 5 / 16 / 982`) | 55 / 57 (`96.49 %`) | `0.7040` / `0.1063` (`324` prov.) | `929.0` / `1908.35` / `2451.0` | `731.73 MB` / — | Cumple / Cumple |

### Audio 2 — `clase_02_cerca.wav` (`414.21 s`, `899` palabras, `70` menciones de glosario, `54` segmentos finales)

| Configuración | Ritmo | WER (`S / D / I / N`) | Glosario recuperado | RTF total (c/ prov.) / finales | Latencia servidor (med / p95 / máx ms) | Mem. proc. / Δ GPU | Meta `RNF03` / `RNF01` srv |
|---|---|---|---|---|---|---|---|
| **`small` · CUDA · prompt=Sí** | `1x` real | **3.56 %** (`24 / 0 / 8 / 899`) | **67 / 70 (`95.71 %`)** | `0.2841` / `0.0426` (`359` prov.) | `435.0` / **`821.05`** / `941.0` | `1047.12 MB` / `+82 MB` | Cumple / Cumple |
| `small` · CUDA · prompt=No | `--rapido` | 5.01 % (`36 / 0 / 9 / 899`) | 56 / 70 (`80.00 %`) | — / `0.0415` (`0` prov.) | n/a (`--rapido`) | `1186.95 MB` / `+82 MB` | Cumple / n/a |
| `base` · CPU · prompt=Sí | `1x` real | 9.45 % (`55 / 11 / 19 / 899`) | 61 / 70 (`87.14 %`) | `0.7091` / `0.1063` (`325` prov.) | `961.5` / `2250.70` / `3476.0` | `734.94 MB` / — | Cumple / Cumple |

### Hallazgos clave de ASR
1. **Impacto cuantificado de `ASR_PROMPT_GLOSARIO`:** activar el contexto del glosario redujo el WER en ambos audios (`3.97 % → 3.16 %` y `5.01 % → 3.56 %`), pero su mayor efecto estuvo en los términos técnicos de `clase_02_cerca.wav`: la recuperación subió de **`80.00 %` (`56/70`) a `95.71 %` (`67/70`)**. Sin prompt, el término `"tabla hash"` cayó a `2/6` menciones recuperadas (transcrito erróneamente), mientras que con prompt alcanzó `6/6`.
2. **Costo real de los provisionales cada 1 s:** ejecutar solo los segmentos finales en `base` CPU reporta `RTF = 0.1063`, pero a ritmo real con ventanas provisionales cada `1000 ms` (`324–325` inferencias intermedias) el factor de tiempo real sube a **`0.7040–0.7091`** (~71 % de ocupación continua de CPU) y la latencia p95 alcanza `1908–2251 ms`. En cambio, `small` en GPU CUDA mantiene **`RTF total = 0.2841–0.3069`** con p95 de **`804.55–821.05 ms`**.
3. **Pico puntual de cola (`3595 ms`) en `clase_01` (`small` CUDA):** correspondió al segmento 21 (`11.19 s` continuos sin pausa de `600 ms`), donde la acumulación secuencial de provisionales retrasó el cierre del segmento; la lógica de salto de provisionales mantuvo el flujo estable y el segmento siguiente (22) retornó a `353 ms`.
4. **Pérdida residual de términos en `clase_02` (`67/70`):** de las `3` menciones perdidas con `small` + prompt, `2` correspondieron a `"nodo"` confundido acústicamente (`"uno"` / `"nuevos"`) y `1` a `"árbol binario"` transcrito sin tilde (`"arbol binario"`).

---

## 3. Mapeo de conceptos del glosario frente a `RNF04`

Meta preliminar de referencia: **`RNF04` (`precisión ≥ 90 %` y `recuperación ≥ 85 %`)** evaluado sobre la partición protegida `"prueba"`.

### Origen y separación temporal (`R11–R12`)
Las `102` frases de `ml/datos/frases_anotadas.jsonl` fueron redactadas por el autor sobre `INF-221` (sin grabaciones ni textos de terceros). Las `66` frases de `"prueba"` se redactaron y congelaron en el commit `04c6c7f` **antes** de definir formas admitidas y bloqueos en `SPEC-007` (`4783e1b`), sin modificarse tras medir.

### Resultados agregados

| Partición | Frases | TP / FP / FN | Precisión | Recuperación | F1 | Compuestos (`P / R`) | Cobertura | Meta `RNF04` |
|---|---|---|---|---|---|---|---|---|
| **`"prueba"` (protegida)** | `66` | `79 / 3 / 2` | **96.34 %** (`0.9634`) | **97.53 %** (`0.9753`) | `0.9693` | **`100.0 % / 100.0 %`** (`21 / 0 / 0`) | `81/81` (`1.0`) | **Cumple** |
| `"ajuste"` (referencia interna) | `36` | `40 / 0 / 0` | `100.0 %` (`1.0`) | `100.0 %` (`1.0`) | `1.0` | `100.0 % / 100.0 %` (`9 / 0 / 0`) | `40/40` (`1.0`) | — |

Desglose por tipo en `"prueba"`:
- **Conceptos compuestos (`4` términos, `21` menciones):** `TP=21, FP=0, FN=0` (`100.0 %` precisión y recuperación en *lista enlazada*, *árbol binario*, *tabla hash*, *búsqueda binaria*).
- **Conceptos simples (`11` términos, `60` menciones):** `TP=58, FP=3, FN=2` (precisión `95.08 %`, recuperación `96.67 %`, `F1 = 0.9587`).
- Todos los conceptos tuvieron `P = 1.0` y `R = 1.0` excepto `cola` (`TP=4, FP=1`, prec `0.80`), `pila` (`TP=5, FP=2`, prec `0.7143`) y `memoria` (`TP=4, FN=2`, rec `0.6667`).

### Listado completo de errores en `"prueba"` (`5` frases de `66`)

1. **Falsos positivos por bloqueos finitos no presentes en `"ajuste"` (`3` casos):**
   - `L9`: *"había una **cola** larga afuera de la oficina de docencia"* → `FP=['cola']`.
   - `L10`: *"dejé una **pila** de pruebas corregidas sobre el mesón"* → `FP=['pila']`.
   - `L11`: *"se descargó la **pila** del micrófono así que hablaré más fuerte"* → `FP=['pila']`.
   *(Muestra la limitación inherente de enumerar bloqueos por frase fija frente a contextos figurados o cotidianos nuevos.)*
2. **Falsos negativos por sobrefiltrado de bloqueo amplio (`2` casos):**
   - `L44`: *"una fuga **de memoria** ocurre cuando olvidamos liberar lo asignado"* → `FN=['memoria']` (suprimido por el bloqueo `"de memoria"`).
   - `L63`: *"si falla la asignación **de memoria** el puntero queda inválido"* → `FN=['memoria']` (suprimido por el bloqueo `"de memoria"`).
   *(Evidencia un compromiso directo del mecanismo actual: bloquear el bigrama `"de memoria"` evita el uso idiomático `"aprender de memoria"`, pero suprime sintagmas nominales técnicos compuestos como `"fuga de memoria"` y `"asignación de memoria"`.)*

---

## 4. Distribución WebSocket bajo concurrencia frente a `RNF06`

Meta preliminar de referencia: **`RNF06` (`1` fuente + `20` receptores en una sala; `2` salas concurrentes con `1` fuente + `10` receptores cada una)**.  
Ejecutadas contra `uvicorn` nativo (puerto `8001` por ocupación del puerto `8000` en la estación) con `ASR_PROVIDER=stub` (`STUB_INTERVAL_MS=1500`) para aislar el fan-out de mensajes de la inferencia ASR.

| Escenario | Salas y receptores | Duración | Emitidos / Recibidos | Perdidos / Dup. / Fuera orden / Err. | Retardo entrega (med / p95 / máx ms) | CPU servidor (med / p95 / máx %) | RSS servidor (med / máx MB) | Meta `RNF06` (local `stub`) |
|---|---|---|---|---|---|---|---|---|
| **Escenario A** (`1 + 20`) | `INF-221-1` (`20` rec.) | `302.81 s` | `197` / `3940` | `0 / 0 / 0 / 0` | `1.0` / `4.0` / `12.0` | `1.5` / `4.6` / `84.1`* | `337.67` / `338.15` | **Cumple** |
| **Escenario B** (`2 × (1 + 10)`) | `INF-221-1` (`10`) + `MAT-101-3` (`10`) | `300.16 s` | `197 + 197` / `1970 + 1970` | `0 / 0 / 0 / 0` | S1: `1.0` / `3.0` / `11.0`<br>S2: `1.0` / `3.0` / `7.0` | `1.5` / `4.7` / `9.3` | `346.69` / `347.22` | **Cumple** |

*\* El pico de CPU de `84.1 %` en el Escenario A coincide con la carga inicial de `es_core_news_md` (`spaCy`) en memoria (`RSS 197.73 MB → ~338 MB`) al procesarse el primer segmento final.*

---

## 5. Limitaciones y metas no cubiertas en esta etapa

1. **Voz única y lectura de guion:** las cifras ASR provienen de lectura preparada del autor (`3.16–3.56 %` WER con `small` GPU). En un aula real con habla espontánea, vacilaciones, cambios de ritmo y distintos docentes el error esperable será mayor; estas mediciones sirven para comparar configuraciones y detectar cuellos de botella, no para extrapolar desempeño en sala real.
2. **Brecha en la condición acústica degradada (`R9`):** aunque se ensamblaron dos muestras independientes de ~`6.7` y ~`6.9` minutos, ambas fueron captadas con micrófono cercano en ambiente silencioso. **No se midió todavía** el efecto de mayor distancia micrófono–hablante ni de ruido ambiente real (ventilación, murmullo de aula), por lo que esa parte de `R9` queda declarada pendiente.
3. **Sin evaluación con usuarios ni validación PIESDI:** la comprensión de señas, carga cognitiva en pantalla, usabilidad (SUS) y pertinencia lingüística de señas reales quedan fuera de esta PoC y pertenecen al trabajo con PIESDI e informe final de Proyecto de Título (2027).
4. **Latencia parcial (`RNF01` solo en servidor):** las mediciones no incluyen la trama inicial en el navegador (`100 ms`), el envío por Wi-Fi/HTTPS ni el tiempo de renderizado del video/subtítulo en los clientes móviles.
5. **Sesgo de diseño y alcance del glosario:** aunque la partición `"prueba"` se congeló antes de ajustar reglas, el mismo autor redactó frases y reglas. Adicionalmente, `spaCy` + bloqueos estáticos no resuelven el compromiso `"de memoria"` vs `"fuga/asignación de memoria"`, y un error puntual de acentuación en ASR (`"arbol binario"`) basta para omitir un término en el glosario.
6. **Carga ejecutada con `ASR_PROVIDER=stub` en `localhost`:** valida la capa WebSocket/fan-out en 1 y 2 salas con 20 receptores sin pérdidas, pero no mide contención de inferencia GPU cuando dos aulas transmiten audio simultáneamente bajo tráfico real en Wi-Fi.

---

## 6. Configuración propuesta para continuar

Para cerrar el Anteproyecto (`SPEC-009`) y proyectar el piloto de Proyecto de Título se propone mantener como línea base:

- **`ASR_PROVIDER=whisper`**, **`WHISPER_MODEL=small`**, **`WHISPER_DEVICE=auto`** (usando GPU CUDA `float16` cuando exista, como en la RTX 3050 medida con `WER 3.16–3.56 %`, `95.71–100 %` en glosario y `p95 ~0.82 s`).
- **`ASR_PROMPT_GLOSARIO=true`**: imprescindible dada la caída observada de recuperación terminológica (`95.71 % → 80.00 %` en Audio 2 sin prompt).
- **Respaldo sin GPU:** en despliegues sin CUDA (`WHISPER_DEVICE=cpu`), fijar `WHISPER_MODEL=base` (`int8`), donde cumple tiempo real (`RTF total ~0.71`, `WER 8.25–9.45 %`, `p95 ~1.9–2.3 s`), evaluando subir `ASR_PARCIAL_MS` (p. ej. a `1500 ms`) si la CPU comparte otras tareas.
- **Parámetros de segmentación:** conservar `ASR_SILENCIO_MS=600`, `ASR_PARCIAL_MS=1000`, `ASR_MAX_SEGMENTO_MS=15000` y `ASR_FLUSH_TIMEOUT_MS=5000`.
- **Siguientes pasos técnicos derivados de la evidencia:** (1) ejecutar `SPEC-009` para control de acceso por inscripción, `puede_capturar`, pausa compartida y seguridad; (2) incorporar una grabación con ruido de aula / micrófono a distancia para cerrar la brecha de `R9`; y (3) para el motor NLP en Proyecto de Título, agregar tolerancia acentual y bloqueos con excepciones positivas / análisis sintáctico para no bloquear términos compuestos como `"fuga de memoria"`.
