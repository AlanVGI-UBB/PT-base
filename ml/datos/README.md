# Datos de evaluación de la PoC (`ml/datos/`)

## Origen y separación de particiones (`SPEC-008` R11–R12, `RNF04`)

- **`frases_anotadas.jsonl`:** conjunto de 102 frases en español sobre el curso piloto provisional `INF-221` (*Estructuras de Datos*), redactadas por el autor a partir de explicaciones y vocabulario típico de la asignatura (sin grabaciones ni textos de terceros).
  - **Partición `"prueba"` (66 frases):** redactada y congelada el **2026-11-19**, **antes** de definir las formas admitidas y los bloqueos en `backend/data/seed_glosario.json` (`SPEC-007`). No se utiliza para ajustar reglas del glosario ni del motor de coincidencia. Incluye frases sin conceptos, usos cotidianos o ambiguos de palabras del glosario (*"de memoria"*, *"cola larga"*, *"pila de pruebas"*, *"pila del micrófono"*, *"llegamos a un arreglo"*, *"tabla de notas"*), términos compuestos y flexiones.
  - **Partición `"ajuste"` (36 frases):** separada para diseñar y validar reglas, formas y bloqueos durante la implementación de `SPEC-007`.

## Conceptos cubiertos (glosario piloto provisional `INF-221`)

`arreglo`, `lista enlazada`, `pila`, `cola`, `árbol binario`, `nodo`, `puntero`, `grafo`, `tabla hash`, `recursión`, `algoritmo`, `complejidad`, `ordenamiento`, `búsqueda binaria`, `memoria`.

## Corpus de audio propio (`SPEC-008` R9–R10)

Los audios grabados con voz del autor se ubican en `ml/datos/audio/` (ignorado por Git en `.gitignore`) en formato **WAV PCM mono, 16 bits, 16 000 Hz**. Los guiones de lectura y sus transcripciones de referencia revisadas contra cada grabación se versionan en `ml/datos/guiones/` y `ml/datos/referencias/`.

### Fichas de grabaciones

*Nota sobre origen:* ambas clases fueron grabadas por el autor mediante la aplicación de grabadora de audio de su teléfono móvil (`AAC 48 kHz estéreo` en `.m4a`, divididas por párrafo/tramo) y ensambladas en orden (`C1P1..C1P8-3`, `10` tramos; `C2P1..C2P7-3`, `16` tramos) a WAV PCM mono `16 bits / 16 000 Hz` con `ffmpeg`. Ambas referencias fueron revisadas directamente contra el audio para reflejar variantes efectivamente pronunciadas (p. ej. `"en las estructuras"`, `"qué estructuras"`, `"consumirá"`, `"utilizado en árboles binarios"`, `"entre unidades"`).

- **`clase_01_cerca.wav`**
  - Guion: `ml/datos/guiones/clase_01.txt` (`982` palabras)
  - Referencia: `ml/datos/referencias/clase_01.txt` *(revisada contra los 10 tramos de audio)*
  - Micrófono y formato fuente: teléfono móvil del autor (`M4A AAC 48 kHz 2 ch`, toma cercana; ruido de fondo medido `RMS p10 = 0.00334`, señal `p50 = 0.09471`)
  - Lugar: domicilio del autor *(detalle específico de ambiente pendiente de confirmar por el autor)*
  - Fecha: `2026-11-20` (`19:13–19:41` hora local)
  - Duración: `404.65 s` (`6 min 44.65 s`)

- **`clase_02_cerca.wav`**
  - Guion: `ml/datos/guiones/clase_02.txt` (`899` palabras)
  - Referencia: `ml/datos/referencias/clase_02.txt` *(revisada contra los 16 tramos de audio)*
  - Micrófono y formato fuente: teléfono móvil del autor (`M4A AAC 48 kHz 2 ch`, toma cercana en ambiente silencioso; ruido de fondo medido `RMS p10 = 0.00254`, señal `p50 = 0.09080`)
  - Lugar: domicilio del autor *(grabación cercana en ambiente silencioso)*
  - Fecha: `2026-11-20` (`19:43–20:50` hora local)
  - Duración: `414.21 s` (`6 min 54.21 s`)

> *Brecha declarada respecto a R9:* ambas muestras entregadas fueron grabadas en condición cercana y ambiente silencioso. Queda pendiente incorporar una toma adicional a mayor distancia o con ruido ambiente real para cubrir el escenario acústico degradado de R9.

