# SPEC-008 — Mediciones de la prueba de concepto: transcripción, coincidencia y distribución

**Etapa del plan:** adelanto de Semestre 2 · Etapa 6 ("instrumenta el logging desde ya") de `docs/plan_desarrollo_tecnico.md`. Propuesta: Mes 4 del anteproyecto ("consolidación de resultados preliminares") y actividades AP Obj. 2 Act. 1 y Obj. 3 Act. 1. Informe: §3.5.1, RNF01, RNF03, RNF04, RNF06, RNF16, Tabla 4.1 y Tabla 4.10.
**Estado:** Implementada — mediciones ejecutadas y documentadas en `docs/resultados_poc.md` (brecha declarada en R9: las dos grabaciones del autor fueron cercanas y silenciosas; queda pendiente una toma con ruido ambiente o mayor distancia).
**Depende de:** SPEC-006, SPEC-007

---

## 1. Objetivo

Producir evidencia medida y reproducible de la PoC: error de transcripción, latencia del servidor, calidad del mapeo de conceptos y comportamiento con varios receptores. El informe declara la factibilidad técnica "condicionada a la PoC" y hoy no existe ninguna medición.

## 2. Contexto y supuestos

- **Estado actual:** `evaluation/logging.py` no se usa desde SPEC-004 y escribe en tablas (`sesion`, `segmento`) que nadie lee. `ml/` solo contiene `.gitkeep`. No hay corpus, transcripciones de referencia ni frases anotadas.
- **Metas preliminares del informe** (no son compromisos aceptados; se reporta contra ellas):
  - RNF01: percentil 95 de hasta 5 s entre el fin del habla del segmento y su texto final visible.
  - RNF03: WER de hasta 25 % en un corpus autorizado del curso.
  - RNF04: precisión de al menos 90 % y recuperación de al menos 85 % sobre menciones anotadas.
  - RNF06: una fuente y 20 receptores en una sesión; dos sesiones con una fuente y 10 receptores cada una.
- **Corpus posible en esta etapa:** grabaciones de la voz del propio autor. No hay autorización para grabar a docentes ni a otras personas, y el informe exige esa autorización antes de capturar. Por lo tanto los resultados no representan un aula real y así se declara.
- **Las reglas no se ajustan con los datos de evaluación** (RNF04): el conjunto de frases se divide en una partición de ajuste y una de prueba.
- **Equipo de medición:** el de desarrollo (RTX 3050 Laptop de 6 GB). Cada resultado registra el hardware y las versiones con que se obtuvo.
- Los scripts de medición se ejecutan con el backend nativo, no en Docker.

## 3. Alcance

### Incluido

1. Instrumentación de tiempos por segmento en el servidor.
2. `ml/evaluar_asr.py`: WER, latencia y factor de tiempo real por configuración.
3. `ml/evaluar_matching.py`: precisión y recuperación sobre frases anotadas.
4. `ml/prueba_carga.py`: distribución a receptores simulados.
5. Corpus de prueba propio y conjunto de frases anotadas.
6. `docs/resultados_poc.md` con los resultados y sus condiciones.

### Explícitamente fuera

- Evaluación con usuarios (comprensión de clips, SUS, tareas de usabilidad): requiere participantes y acuerdos con PIESDI.
- Audio de clases reales o de terceros.
- Latencia medida hasta el texto visible en el dispositivo del receptor (RNF01 completo): exige sincronizar relojes entre cliente y servidor.
- Comparación con un ASR remoto.
- Auditoría de accesibilidad WCAG, disponibilidad y pruebas de respaldo (RNF08, RNF12, RNF13).

## 4. Requisitos

1. **R1 — Tiempos por segmento:** por cada segmento final el servidor registra en `metrica_segmento`: tiempo de audio de inicio y fin, instante de llegada de la trama que contiene el fin del segmento, duración de la inferencia, duración del matching, instante de difusión y número de receptores conectados. Los instantes se toman con reloj monotónico y se guardan relativos al inicio de la sesión.
2. **R2 — Latencia del servidor definida:** `latencia_servidor_ms = emitido_ms − llegada_fin_ms`. La documentación indica qué excluye: la trama de captura (100 ms), la red y el renderizado en el cliente.
3. **R3 — Instrumentación desactivable:** `METRICAS=false` deja de escribir en `metrica_segmento` sin cambiar el comportamiento de la sala. Por defecto está activa.
4. **R4 — Evaluación de ASR por el mismo camino:** `ml/evaluar_asr.py` alimenta un WAV de 16 kHz mono, trama por trama y a ritmo real, al mismo `Segmentador` y `FasterWhisperProvider` que usa la sala. No transcribe el archivo completo de una vez.
5. **R5 — Métricas de ASR:** el script reporta WER con sus conteos (S, D, I, N), factor de tiempo real, latencia del servidor (mediana, percentil 95 y máximo), número de segmentos, memoria máxima del proceso y memoria de GPU cuando exista.
6. **R6 — Normalización fija:** la normalización previa al WER (minúsculas, sin puntuación, Unicode NFC, números tal como se transcriben) está en `ml/normalizacion.py`, tiene pruebas y se aplica igual a todas las configuraciones.
7. **R7 — Términos técnicos por separado:** el script reporta, además del WER global, la fracción de menciones de conceptos del glosario presentes en la referencia que aparecen en la transcripción.
8. **R8 — Configuraciones comparables:** el script recibe modelo, dispositivo, precisión y uso del contexto de vocabulario (`ASR_PROMPT_GLOSARIO`). Todas las configuraciones se miden con los mismos audios.
9. **R9 — Corpus propio:** existen al menos dos grabaciones de 5 a 10 minutos con voz del autor leyendo un guion con contenido del curso piloto: una con micrófono cercano en ambiente silencioso y otra con ruido ambiente o mayor distancia. Cada una tiene su transcripción de referencia revisada contra el audio y una ficha con micrófono, lugar, fecha y duración.
10. **R10 — Audio fuera del repositorio:** los WAV viven en `ml/datos/audio/`, que se agrega a `.gitignore`. Se versionan los guiones, las referencias y las fichas.
11. **R11 — Frases anotadas:** `ml/datos/frases_anotadas.jsonl` contiene al menos 30 frases de ajuste y 60 de prueba. Cada frase declara sus conceptos esperados y su partición. La partición de prueba incluye frases sin conceptos, usos no técnicos de palabras del glosario, expresiones compuestas y flexiones.
12. **R12 — Partición de prueba protegida:** las frases de prueba se redactan o extraen de material del curso antes de ajustar formas y bloqueos, y no se usan para ajustarlos. El documento de resultados declara el origen de las frases.
13. **R13 — Métricas de mapeo:** `ml/evaluar_matching.py` reporta verdaderos positivos, falsos positivos y falsos negativos, precisión y recuperación, globales y por concepto, con los compuestos por separado y el listado de cada error.
14. **R14 — Prueba de carga:** `ml/prueba_carga.py` ejecuta contra un backend en marcha el escenario A (una sala, 1 emisor y 20 receptores, 5 minutos) y el escenario B (dos salas, 1 emisor y 10 receptores cada una). Reporta por receptor los eventos recibidos, perdidos, duplicados y fuera de orden, el retardo de entrega y el uso de CPU y memoria del proceso servidor.
15. **R15 — Marca de tiempo del servidor:** el evento `segmento` incluye `servidor_ms` (hora del servidor al difundir) para que la prueba de carga calcule el retardo de entrega en la misma máquina.
16. **R16 — Resultados trazables:** cada ejecución escribe un JSON en `ml/resultados/` con las métricas, la configuración, el hardware, las versiones de las bibliotecas y el hash del commit. Estos JSON se versionan.
17. **R17 — Documento de resultados:** `docs/resultados_poc.md` presenta condiciones, tablas por configuración frente a cada meta, limitaciones y la configuración que se propone para continuar. Toda cifra del documento proviene de un JSON de `ml/resultados/`. Una meta no alcanzada se informa como no alcanzada.
18. **R18 — Dependencias separadas:** las dependencias de medición van en `ml/requirements.txt` y no se agregan a la imagen del backend.
19. **R19 — Verificación mínima:** `ruff check backend ml`, `pytest backend/tests` y `pnpm --prefix frontend build` pasan. `AGENTS.md` incorpora `ruff check ml` a la verificación.

## 5. Diseño técnico

### 5.1 Archivos

```
backend/app/evaluation/
└── metricas.py            # NUEVO: registrar_segmento(); reemplaza a logging.py
backend/data/schema.sql    # tabla metrica_segmento
ml/
├── requirements.txt       # jiwer, psutil, websockets
├── normalizacion.py
├── evaluar_asr.py
├── evaluar_matching.py
├── prueba_carga.py
├── tests/test_normalizacion.py
├── datos/
│   ├── README.md              # fichas de las grabaciones y origen de las frases
│   ├── guiones/*.txt
│   ├── referencias/*.txt
│   ├── frases_anotadas.jsonl
│   └── audio/                 # en .gitignore
└── resultados/*.json
docs/resultados_poc.md
```

`ml/datos/`, `ml/resultados/` y `ml/tests/` son subdirectorios nuevos dentro de `ml/`, que el plan reserva para "scripts de entrenamiento/experimentación, separados del código de servicio". `docs/resultados_poc.md` corresponde al uso que el plan asigna a `docs/` ("resultados de evaluación").

### 5.2 Instrumentación

```sql
CREATE TABLE IF NOT EXISTS metrica_segmento (
    id INTEGER PRIMARY KEY,
    clase_id INTEGER NOT NULL REFERENCES clase(id),
    segmento_id INTEGER NOT NULL,
    audio_inicio_ms INTEGER NOT NULL,
    audio_fin_ms INTEGER NOT NULL,
    llegada_fin_ms INTEGER NOT NULL,
    asr_ms INTEGER NOT NULL,
    nlp_ms INTEGER NOT NULL,
    emitido_ms INTEGER NOT NULL,
    receptores INTEGER NOT NULL
);
```

- El `Segmentador` de SPEC-006 anota el instante de llegada de cada trama; `Ventana` y `ResultadoASR` ganan `llegada_fin_ms` y `asr_ms`. El stub los entrega en 0.
- El handler mide `nlp_ms` alrededor de `buscar_terminos` y toma `emitido_ms` justo antes del `broadcast`.
- `evaluation/logging.py` y las tablas `sesion` y `segmento` se eliminan (si SPEC-009 ya lo hizo, este punto no aplica).

### 5.3 `ml/evaluar_asr.py`

```powershell
python ml\evaluar_asr.py --audio ml\datos\audio\clase_01_cerca.wav `
  --referencia ml\datos\referencias\clase_01.txt `
  --modelo small --device cuda --prompt-glosario
```

- Importa `Segmentador` y `FasterWhisperProvider` desde `backend/app` y el índice del glosario del curso piloto.
- Lee el WAV con `wave` y entrega tramas de 100 ms respetando su duración real.
- Une los textos finales, normaliza y calcula el WER con `jiwer`.
- Calcula la latencia con la misma definición de R2.
- Opción `--rapido` para alimentar sin esperas: solo es válida para WER y se marca en el JSON.

### 5.4 `ml/evaluar_matching.py`

```json
{"texto": "insertamos un nodo al final de la lista enlazada", "conceptos": ["nodo", "lista enlazada"], "particion": "prueba"}
{"texto": "apréndanse la fórmula de memoria", "conceptos": [], "particion": "prueba"}
```

Compara por frase el multiconjunto de conceptos detectados con el esperado. Una mención cubierta no detectada es un falso negativo; un concepto que no está en el glosario no cuenta como fallo del detector y se reporta aparte como cobertura.

### 5.5 `ml/prueba_carga.py`

- Usa el backend con `ASR_PROVIDER=stub` para aislar la distribución de la inferencia. Una variante opcional usa `whisper` con un WAV del corpus.
- Obtiene un token con el usuario de prueba, abre el emisor y N receptores con `websockets`, y cada receptor guarda `(segment_id, servidor_ms, recibido_ms)`.
- Mide el proceso del servidor con `psutil` a partir de su PID.

### 5.6 `docs/resultados_poc.md`

Secciones: condiciones de medición; transcripción (tabla por configuración y audio frente a RNF03 y RNF01); mapeo (frente a RNF04, con los errores más frecuentes); distribución (frente a RNF06); limitaciones; configuración propuesta para continuar.

## 6. Criterios de aceptación

- [x] R1–R8 y R10–R19 satisfechos (en R9, existen 2 grabaciones propias de ~6.7 y ~6.9 min con referencias revisadas y fichas; ambas en condición cercana silenciosa, quedando declarada la brecha de una toma con ruido/distancia).
- [x] Hay resultados de ASR para al menos dos configuraciones sobre los dos audios (`small` CUDA con prompt a ritmo real, `small` CUDA sin prompt `--rapido`, y `base` CPU con prompt a ritmo real).
- [x] Hay un resultado de mapeo sobre la partición de prueba (`matching_prueba_20261121_005931.json`).
- [x] Hay resultados de los escenarios A y B de carga (`carga_escenario_A_stub_20261119_212452.json`, `carga_escenario_B_stub_20261119_212954.json`).
- [x] Cada cifra de `docs/resultados_poc.md` se puede rastrear a un JSON con su commit.
- [x] El documento declara que el corpus es voz del autor, el tamaño de cada muestra y que no hubo evaluación con usuarios.
- [x] No hay archivos de audio versionados.

## 7. Tareas de implementación

1. `schema.sql`, `evaluation/metricas.py`, tiempos en `Segmentador`, `ResultadoASR` y handler; `servidor_ms` en el evento.
2. `ml/requirements.txt`, `ml/normalizacion.py` y sus pruebas.
3. Redactar los guiones, grabar los audios, revisar las referencias y escribir las fichas.
4. Redactar la partición de prueba de las frases anotadas **antes** de ajustar formas y bloqueos de SPEC-007; después, la de ajuste.
5. `ml/evaluar_asr.py` y ejecución de las configuraciones.
6. `ml/evaluar_matching.py` y ejecución.
7. `ml/prueba_carga.py` y ejecución de los escenarios A y B.
8. `docs/resultados_poc.md`.
9. `.gitignore`, `AGENTS.md`, README.
10. Verificación de §8 y entrada en `docs/historial_implementacion.md`.

## 8. Verificación

```powershell
ruff check backend ml
pytest backend/tests
pytest ml/tests
pnpm --prefix frontend build

pip install -r ml\requirements.txt
python ml\evaluar_asr.py --audio ml\datos\audio\clase_01_cerca.wav --referencia ml\datos\referencias\clase_01.txt --modelo small --device cuda --prompt-glosario
python ml\evaluar_matching.py --datos ml\datos\frases_anotadas.jsonl --particion prueba

# Carga: backend en otra terminal con ASR_PROVIDER=stub
python ml\prueba_carga.py --escenario A --minutos 5
python ml\prueba_carga.py --escenario B --minutos 5

git status --short ml/datos/audio   # no debe listar archivos
```

## 9. Notas / decisiones diferidas

- **Orden con SPEC-007:** la partición de prueba de las frases debe existir antes de ajustar el glosario. Si SPEC-007 se implementa primero, sus formas y bloqueos iniciales se escriben sin mirar esas frases.
- **Sesgo conocido:** el autor escribe las reglas y también las frases. Se reduce tomando las frases de prueba de apuntes o bibliografía del curso; aun así se declara como limitación.
- **Voz única:** una sola voz, leída y no espontánea, subestima el error esperable en aula. Las cifras sirven para elegir configuración y detectar problemas, no para afirmar desempeño en clases reales.
- **Latencia hasta el receptor** y **evaluación con usuarios:** corresponden al piloto de Proyecto de Título, con participantes y condiciones acordadas.
- **Cola de clips:** la densidad de términos por minuto y el retraso de cola (§4.1.4 del informe) se pueden derivar de `evento_clase` y de la duración de los clips; se agrega al documento si alcanza el tiempo.
