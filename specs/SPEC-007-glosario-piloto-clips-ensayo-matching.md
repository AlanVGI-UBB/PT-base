# SPEC-007 — Glosario del curso piloto provisional, clips de ensayo y motor de coincidencia

**Etapa del plan:** Semestre 1 · Etapa 2 (glosario y esquema) y Etapa 3 (PoC con 10–15 términos) de `docs/plan_desarrollo_tecnico.md`. Propuesta: actividad AP Obj. 3 Act. 1 ("Pruebas preliminares del pipeline NLP con spaCy para validación PoC"). Informe: RF13, RF14, RF17, RF18, RN05–RN08, RN10, RN12, §2.2.2, §4.1.4 y §4.2.2.
**Estado:** Completada — verificado (`ruff check backend`, `pytest backend/tests` 54 passed + 1 skipped, `pnpm --prefix frontend build` OK, 15 clips generados y seed sembrado; pendiente prueba con Docker daemon y prueba manual en navegador)
**Depende de:** SPEC-006 (el matching se ejecuta solo sobre texto final)

---

## 1. Objetivo

Dejar la PoC con un glosario coherente de un solo curso, clips que realmente se reproducen y un motor de coincidencia que reconozca variantes, se abstenga en usos conocidos como ambiguos y no dependa de lemas ajustados a mano. Los clips son de ensayo: esta spec no produce ni valida señas.

## 2. Contexto y supuestos

- **Hallazgos sobre los datos** (revisión del 2026-11-16):
  - `seed_glosario.json` tiene 4 cursos ficticios y 29 filas de términos (19 distintos). El curso INF-221 "Estructuras de Datos" contiene términos de cálculo (derivada, integral, límite).
  - Hay términos genéricos (clase, duda, ejercicio, resultado, hablar) que no son vocabulario técnico y generan activaciones sin valor.
  - Los 12 archivos de `backend/data/videos_senas/` pesan 28 bytes: no son videos. Siete términos apuntan al clip de otro (vector → `derivada.mp4`, matriz → `integral.mp4`, fuerza → `derivada.mp4`, velocidad → `integral.mp4`, energía → `resultado.mp4`, ética → `clase.mp4`, valor → `resultado.mp4`).
  - `backend/data/videos_senas/` está en `.gitignore` (línea 24) y no tiene archivos versionados. En un clon limpio la carpeta no existe: `StaticFiles` lanza `RuntimeError` al importar `main.py` y el `COPY data/videos_senas/` del Dockerfile falla.
- **Hallazgos sobre el motor** (`glossary/matching.py`, spaCy 3.8.13 con `es_core_news_md` 3.8.0):
  - La clave es el lema que devuelve spaCy, escrito a mano en el seed ("derivado", "raíz cuadrado"). El lema cambia según el contexto: "entonces resultado es importante" y "entonces ética es importante" no activan nada aunque el término está literal.
  - Falsos positivos observados: "la clase Nodo tiene un puntero" activa *clase*; "no hay límite de tiempo para la tarea" activa *límite*.
  - Omisiones observadas: "esta función es continua" (compuesto discontinuo) y "derivamos la función y después integramos" (formas verbales).
  - Costo medido: unos 3 ms por frase.
  - Esta muestra es pequeña y hecha a mano; la medición formal es de SPEC-008.
- **Hallazgos sobre la presentación:** `SalaView.jsx:115-119` muestra todas las señas del segmento a la vez, en bucle, y las oculta a los 4 s. Un clip real más largo quedaría cortado, y una mención nueva reemplaza a la anterior sin aviso.
- **Sin validación lingüística disponible:** con PIESDI solo hubo la reunión inicial. No hay curso piloto acordado, ni señas acordadas, ni grabaciones. El informe (§2.2.2 y §4.2.1) admite una integración técnica con recursos de ensayo, sin dar por cumplido el OE1.
- **Las señas no se inventan** (RF14, RN08). Por eso los clips de ensayo son tarjetas generadas, sin ninguna persona ni configuración manual: no afirman nada sobre LSCh.
- La base de datos local es descartable: está en `.gitignore` y el seed la borra y repuebla. Los cambios de esquema de esta spec se aplican recreándola.

## 3. Alcance

### Incluido

1. Seed con un curso piloto provisional y un curso de control sin glosario.
2. Estado del recurso por término (`ensayo`, `publicado`, `retirado`) y rótulo visible de "clip de ensayo".
3. Clips de ensayo generados por script y versionados en el repositorio.
4. Formas admitidas por concepto e índice de búsqueda construido por el sistema.
5. Bloqueos: expresiones que consumen el texto sin activar seña.
6. Registro de abstenciones por segmento.
7. Cola de reproducción acotada y agrupación de menciones repetidas en el cliente.
8. Pruebas del motor y de integridad del seed.

### Explícitamente fuera

- Selección real del curso piloto, co-diseño con intérpretes, grabación y validación de señas (OE1, actividades AP 1 a 3). No se resuelven con software.
- Glosario de 80 a 150 términos.
- Administración del glosario desde la aplicación, fichas de revisión y versionado (RF24–RF27, RN11).
- Reglas de glosas y reordenamiento sintáctico (RF15), planificadas para Proyecto de Título.
- Compuestos discontinuos y desambiguación por contexto semántico.
- Protección de acceso a los clips (→ SPEC-009).

## 4. Requisitos

1. **R1 — Curso piloto único:** el seed contiene el curso piloto provisional INF-221 "Estructuras de Datos" con entre 12 y 15 conceptos propios de esa asignatura, y un segundo curso sin términos que sirve para probar el aislamiento entre salas. Se eliminan los cursos y términos restantes y los términos genéricos.
2. **R2 — Carácter provisional declarado:** `seed_glosario.json` y el README indican que el curso y la lista de conceptos son una propuesta del autor para la PoC, sin acuerdo con PIESDI ni con un docente.
3. **R3 — Formato del término:** cada término del seed declara `concepto`, `formas` (una o más expresiones admitidas), `bloqueos` (cero o más), `video` y `estado`. Ya no se escriben lemas a mano.
4. **R4 — Estado del recurso:** `termino.estado` admite `ensayo`, `publicado` y `retirado`. Un término `retirado` no se activa. Todo el seed queda en `ensayo`; `publicado` se reserva para recursos con revisión lingüística.
5. **R5 — Clips de ensayo reproducibles:** existe un clip por concepto, generado por `backend/scripts/generar_clips_ensayo.py` con `ffmpeg`: H.264 en MP4 con inicio rápido, 640×360, 3 s, con el texto "CLIP DE ENSAYO" y el concepto. Ningún clip muestra a una persona.
6. **R6 — Clips versionados:** se retira `backend/data/videos_senas/` de `.gitignore` y los clips de ensayo se confirman en git. Un clon limpio arranca en modo nativo y construye en Docker sin pasos manuales.
7. **R7 — Rótulo de ensayo:** cuando la seña tiene `estado = "ensayo"`, el reproductor muestra "Clip de ensayo · sin validación lingüística" en vivo y en replay.
8. **R8 — Índice construido por el sistema:** al crear la sala, el servidor procesa cada forma con el mismo pipeline de spaCy y registra dos claves por forma: la de lemas y la de formas en minúscula. Ambas excluyen las categorías que hoy se filtran (`DET`, `ADP`, `CCONJ`, `SCONJ`) y la puntuación. El índice se guarda en caché por curso.
9. **R9 — Búsqueda con doble clave:** en cada posición el motor prueba primero el n-grama más largo posible y, para cada longitud, la clave de lemas y luego la de formas. La longitud máxima es la del n-grama más largo del índice, no un valor fijo.
10. **R10 — Bloqueos:** una expresión declarada como bloqueo entra al índice como coincidencia sin seña. Si gana por longitud, consume sus palabras, no activa ningún clip y queda registrada como abstención.
11. **R11 — Claves sin ambigüedad:** si dos conceptos del mismo curso producen la misma clave, el seed falla con un mensaje que nombra ambos conceptos.
12. **R12 — Texto detectado:** cada coincidencia incluye `texto_detectado`, el tramo exacto del texto original. El resaltado del subtítulo usa ese tramo, de modo que una forma distinta del nombre del concepto también queda resaltada.
13. **R13 — Abstenciones registradas:** las abstenciones de un segmento se guardan en `evento_clase.abstenciones_json`. No se difunden a los clientes.
14. **R14 — Reproducción completa y en orden:** el cliente reproduce una seña a la vez, completa y sin bucle; al terminar pasa a la siguiente. Se elimina el ocultamiento fijo a los 4 s.
15. **R15 — Cola acotada visible:** la cola admite hasta 3 señas pendientes. Si llega otra con la cola llena, se descarta la pendiente más antigua y se suma a un contador. El panel muestra cuántas señas hay en cola y cuántas se omitieron, con el texto "disponibles en el historial".
16. **R16 — Menciones repetidas:** una seña no se encola si el mismo concepto se está reproduciendo, está en cola o terminó de reproducirse hace menos de 20 s. El término sigue resaltado en el subtítulo y el evento sigue completo en el historial.
17. **R17 — Historial fiel:** el servidor persiste todas las coincidencias de cada segmento final. La cola y la agrupación de R15 y R16 son solo de presentación.
18. **R18 — Replay:** en modo replay se reproduce una vez el clip del evento actual, con el mismo rótulo de R7.
19. **R19 — Pruebas del motor:** hay pruebas de formas admitidas, doble clave (un término que el lematizador altera se reconoce por su forma), bloqueo, término retirado, n-grama más largo y `texto_detectado`.
20. **R20 — Pruebas del seed:** una prueba recorre el seed real y verifica que cada forma declarada se reconoce dentro de tres frases portadoras, que cada `video` existe y pesa más de 1 kB, y que no hay claves ambiguas.
21. **R21 — Verificación mínima:** `ruff check backend`, `pytest backend/tests` y `pnpm --prefix frontend build` pasan sin errores.

## 5. Diseño técnico

### 5.1 Seed

```json
{
  "nota": "Curso piloto y glosario PROVISIONALES para la PoC. Sin acuerdo con PIESDI ni validación lingüística.",
  "cursos": [
    {"id": 1, "cod_ramo": "INF-221", "nombre": "Estructuras de Datos"},
    {"id": 2, "cod_ramo": "MAT-101", "nombre": "Álgebra Lineal"}
  ],
  "terminos": [
    {
      "curso_id": 1,
      "concepto": "lista enlazada",
      "formas": ["lista enlazada", "listas enlazadas", "lista ligada"],
      "bloqueos": [],
      "video": "lista_enlazada.mp4",
      "estado": "ensayo"
    },
    {
      "curso_id": 1,
      "concepto": "memoria",
      "formas": ["memoria"],
      "bloqueos": ["de memoria"],
      "video": "memoria.mp4",
      "estado": "ensayo"
    }
  ]
}
```

Conceptos propuestos para el curso piloto provisional: arreglo, lista enlazada, pila, cola, árbol binario, nodo, puntero, grafo, tabla hash, recursión, algoritmo, complejidad, ordenamiento, búsqueda binaria y memoria. Las formas y los bloqueos de cada uno se completan al implementar, apoyándose en la prueba de R20.

### 5.2 Esquema

```sql
CREATE TABLE IF NOT EXISTS termino (
    id INTEGER PRIMARY KEY,
    curso_id INTEGER NOT NULL REFERENCES curso(id),
    texto_visible TEXT NOT NULL,          -- nombre del concepto
    formas_json TEXT NOT NULL,            -- ["lista enlazada", ...]
    bloqueos_json TEXT NOT NULL DEFAULT '[]',
    video_url TEXT NOT NULL,
    estado TEXT NOT NULL DEFAULT 'ensayo' -- ensayo | publicado | retirado
);
```

Se eliminan `termino.lema` y `termino.n_palabras`. `evento_clase` gana la columna `abstenciones_json TEXT`. Se conserva el nombre `texto_visible` para no tocar el resto del código.

### 5.3 Motor (`glossary/`)

```
backend/app/glossary/
├── repository.py   # list_terminos con formas, bloqueos y estado
├── indice.py       # NUEVO: construir_indice(terminos) → Indice; caché por curso
└── matching.py     # buscar_terminos(texto, indice) → Coincidencias
```

```python
@dataclass
class Coincidencias:
    senas: list[dict]         # termino_id, texto_visible, video_url, estado, texto_detectado
    abstenciones: list[dict]  # bloqueo, texto_detectado

@dataclass
class Indice:
    entradas: dict[str, dict | None]   # clave → término, o None si es bloqueo
    max_ngrama: int
```

- `construir_indice` omite los términos `retirado`, procesa cada forma y cada bloqueo con `get_nlp()` y registra la clave de lemas y la de formas. Si una clave ya pertenece a otro concepto lanza `ValueError` (R11). Un bloqueo y un término pueden coexistir porque el bloqueo siempre es más largo que la forma que contiene; si no lo es, el seed falla.
- `buscar_terminos` conserva los índices de los tokens originales para recuperar `texto_detectado` con `doc[i:j].text`.
- `RoomState` guarda el `Indice` en lugar de `glosario_por_lema`. La caché por curso se invalida al ejecutar el seed.

### 5.4 Clips de ensayo

- `backend/scripts/generar_clips_ensayo.py` lee el seed y, por cada término, ejecuta `ffmpeg` con una fuente de color y texto superpuesto. La ruta de la tipografía es un parámetro, porque el filtro de texto de `ffmpeg` en Windows necesita un archivo de fuente explícito.
- Salida en `backend/data/videos_senas/<video>`. El script no sobrescribe clips existentes salvo con `--forzar`, para no pisar un clip real que reemplace a uno de ensayo.
- El Dockerfile no ejecuta el script: copia los clips ya versionados.

### 5.5 Cliente

```
frontend/src/
├── hooks/useColaSenas.js      # NUEVO: cola, agrupación de repetidas y contadores
├── components/SenaPlayer.jsx  # una seña a la vez, onEnded, rótulo de ensayo, sin bucle
└── views/
    ├── SalaView.jsx           # usa useColaSenas; resaltado por texto_detectado
    └── ClaseDetailView.jsx    # replay: clip del evento actual una vez; mismo resaltado
```

`useColaSenas` expone `actual`, `pendientes`, `omitidas`, `encolar(senas)` y `alTerminar()`. Los límites (3 pendientes, 20 s) son constantes del módulo.

## 6. Criterios de aceptación

- [ ] R1–R21 satisfechos.
- [ ] Un clon limpio del repositorio arranca el backend en modo nativo y construye con `docker compose build` sin crear carpetas a mano.
- [ ] En la sala, decir "vamos a recorrer la lista enlazada" reproduce un clip visible, de principio a fin, con el rótulo de ensayo.
- [ ] Decir "apréndanse esto de memoria" no reproduce ningún clip y deja una abstención en el evento guardado.
- [ ] Nombrar el mismo concepto tres veces en 10 s reproduce el clip una vez; el historial conserva las tres menciones.
- [ ] Nombrar seis conceptos distintos seguidos muestra el contador de señas omitidas y el historial las conserva todas.
- [ ] Una forma distinta del nombre del concepto queda resaltada en el subtítulo.
- [ ] El curso de control no activa ninguna seña.
- [ ] Ningún clip del repositorio muestra a una persona.

## 7. Tareas de implementación

1. Redactar el seed nuevo (cursos, conceptos, formas, bloqueos, nota de provisionalidad).
2. `schema.sql` y `scripts/seed_glosario.py`: formato nuevo de `termino` y validación de claves.
3. `glossary/indice.py`, `glossary/matching.py`, `glossary/repository.py`.
4. `salas/manager.py` y `main.py`: uso del `Indice`, persistencia de abstenciones.
5. `scripts/generar_clips_ensayo.py`; generar los clips; retirar la carpeta de `.gitignore`.
6. `hooks/useColaSenas.js`, `SenaPlayer.jsx`, `SalaView.jsx`, `ClaseDetailView.jsx`, estilos en `App.css`.
7. Pruebas: reescribir `test_matching.py`, agregar `test_indice.py` y `test_seed.py`, ajustar las bases de datos de prueba de `test_sala.py`, `test_historial.py` y `test_schema.py`.
8. README: nota de provisionalidad y de clips de ensayo.
9. Verificación de §8 y entrada en `docs/historial_implementacion.md`.

## 8. Verificación

```powershell
cd backend
.\venv\Scripts\activate
python scripts\generar_clips_ensayo.py
python scripts\seed_glosario.py
cd ..
ruff check backend
pytest backend/tests
pnpm --prefix frontend build

# Clon limpio
git clone . ..\_clon_prueba
cd ..\_clon_prueba
docker compose build

# Manual (con SPEC-006 activa o con el stub ajustado a frases del curso piloto):
#   decir un concepto → clip completo con rótulo de ensayo
#   decir un bloqueo → sin clip
#   repetir un concepto → un solo clip
#   seis conceptos seguidos → contador de omitidas
#   historial → todas las menciones presentes
```

Las frases fijas de `asr/stub.py` se reemplazan por frases del curso piloto para que el modo stub siga mostrando coincidencias.

## 9. Notas / decisiones diferidas

- **El curso piloto es una propuesta.** Se eligió Estructuras de Datos porque ya estaba en el seed y porque la propuesta habla de terminología informática. Cuando PIESDI y un docente acuerden el curso, solo cambia el seed.
- **Clips reales:** cuando existan grabaciones revisadas, reemplazan a las tarjetas y el término pasa a `publicado`. Un clip con una persona es un dato personal: no se confirma en el repositorio sin su autorización y, si el repositorio es público, se guarda fuera de él. Esa decisión de almacenamiento se toma en ese momento.
- **Bloqueos como mecanismo de abstención:** resuelven usos ambiguos conocidos de antemano, no la ambigüedad general (RN06). Los falsos positivos que queden se cuantifican en SPEC-008.
- **Compuestos discontinuos** ("la función es continua") y **formas verbales** de un concepto nominal: las segundas se cubren agregando la forma al seed si el criterio lingüístico lo admite; los primeros quedan como limitación documentada.
- **Límites de la cola (3 pendientes, 20 s):** son valores iniciales. El informe indica que la política final se revisa con usuarios de LSCh.
- **Versionado del glosario** (RF27, RN11): diferido. Mientras tanto, el evento guarda la ruta del clip y el estado vigentes al momento de la clase.
