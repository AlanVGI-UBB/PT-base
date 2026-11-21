# Explicación simple de las pruebas de la PoC (sin tecnicismos)

Esta guía traduce en lenguaje cotidiano qué se midió en [`docs/resultados_poc.md`](resultados_poc.md), cómo se hizo cada prueba, qué significan los números y qué conclusiones honestas puedes sacar para explicar o defender el proyecto.

---

## La idea general: ¿qué queríamos comprobar?

Tu aplicación es como una cadena con **tres eslabones** que trabajan en vivo mientras un profesor habla:

1. **Oído (Transcripción / ASR):** escuchar la voz por pedacitos de audio y pasarla a texto en español.
2. **Filtro inteligente (Mapeo de conceptos):** leer ese texto y decidir qué palabras son términos técnicos del ramo (para mostrar su seña) y cuáles son lenguaje cotidiano (para ignorarlas).
3. **Megáfono (Distribución en sala):** repartir al instante ese texto y esas señas a varios celulares conectados sin perder mensajes ni colapsar el servidor.

Hasta antes de estas pruebas sabíamos que el programa "corría", pero no teníamos números reales para demostrar que funciona bien. Las pruebas de **SPEC-008** midieron esos tres eslabones por separado.

---

## Prueba 1: ¿Qué tan bien escucha y qué tan rápido escribe? (Transcripción / ASR)

### ¿Cómo se probó?
Tomamos tus dos grabaciones ya ensambladas (`clase_01_cerca.wav` de **6 min 45 s** y `clase_02_cerca.wav` de **6 min 54 s**). En lugar de pasarle el archivo entero de golpe, el script lo fue entregando **poco a poco (cada 0,1 segundos)** a la misma velocidad que hablas en la vida real, exactamente como cuando el navegador envía audio por el micrófono durante una clase.

Probamos **tres formas de configurarlo** sobre esos mismos dos audios:
1. **Principal (`small` en tarjeta gráfica RTX 3050 + lista de términos):** la configuración pensada para funcionar en vivo, dándole al modelo una pista previa con los 15 conceptos del ramo (`INF-221`).
2. **Sin pista de términos (`small` en GPU sin lista):** exactamente igual a la anterior, pero sin avisarle qué palabras técnicas existen en el curso, para comprobar si esa ayuda realmente sirve.
3. **Modo respaldo (`base` solo en procesador CPU + lista de términos):** usando un modelo más liviano sin usar la tarjeta gráfica, simulando un computador más modesto sin GPU.

### ¿Qué midieron y qué significa cada dato?

* **Error por palabra (`WER`):** de cada 100 palabras que dijiste, cuántas escribió mal, se saltó o inventó. **La meta era no superar el `25 %` de error.**
  * Con tarjeta gráfica (`small` + lista): falló apenas entre **`3,16 %` y `3,56 %`** (es decir, escribió bien ~97 de cada 100 palabras).
  * En respaldo solo CPU (`base`): falló entre **`8,25 %` y `9,45 %`** (sigue cumpliendo con bastante margen bajo el `25 %`).

* **Conceptos del ramo bien escritos:** no basta con escribir bien palabras comunes; si escribe mal `"árbol binario"` o `"tabla hash"`, después no saldrá el video de la seña.
  * **El gran hallazgo de esta prueba:** en el Audio 2, cuando **no** le dimos al modelo la pista de palabras del ramo, solo logró reconocer bien **`80 %`** de las menciones técnicas (`56` de `70`); por ejemplo, escribió mal `"tabla hash"` `4` de cada `6` veces. Al darle la pista del glosario, saltó a **`95,71 %`** en el Audio 2 (`67` de `70`) y a **`100 %`** en el Audio 1 (`57` de `57`). Quedó demostrado con números que esa ayuda es clave.

* **Velocidad de respuesta (`latencia` y si alcanza en tiempo real):**
  * Piensa en `RTF` (*factor de tiempo real*) como qué porcentaje del reloj necesita el servidor para no atrasarse: si vale menos que `1,0`, alcanza en vivo; si vale más que `1,0`, la fila de frases pendientes crecería sin parar.
  * Mientras hablas sin pausas, el sistema va lanzando **borradores cada 1 segundo** (para que los subtítulos aparezcan rápido en pantalla) y al terminar la frase lanza la **versión final**.
  * Con tarjeta gráfica (`small` CUDA), hacer todos esos borradores más las frases finales solo ocupó alrededor del **`28–31 %`** del tiempo (`RTF = 0,28–0,31`). Típicamente el servidor tardó **`~0,4 segundos`** en entregar la frase final tras cerrar la pausa, y el `95 %` de las frases demoró **`0,82 segundos` o menos** (la meta límite eran `5 segundos`). Solo una frase muy larga de 11 segundos sin pausas acumuló espera puntual hasta `3,6 s`, y en la frase siguiente volvió a `0,35 s`.
  * En respaldo `CPU` (`base`), calcular solo frases finales parece rápido (`~11 %`), pero sumando los borradores de cada segundo el procesador trabajó al **`70–71 %`** (`RTF = 0,70–0,71`). Igual logró mantener los tiempos (`~0,95 s` típico, `95 %` bajo **`1,9–2,25 s`**), pero con poco margen si el mismo computador tuviera que hacer más cosas al mismo tiempo.

---

## Prueba 2: ¿Sabe distinguir un concepto técnico de una charla normal? (Mapeo)

### ¿Por qué tuvimos tanto cuidado en no hacer trampa?
Si uno redacta reglas mirando las mismas frases con las que luego se evalúa, siempre sacará nota `100 %` aunque el sistema falle en la vida real. Para evitar eso, primero redactamos **`66` frases de examen ("partición protegida")**, las guardamos sin tocarlas, y ajustamos el diccionario solo con otra lista aparte (`36` frases de ajuste) antes de evaluar el examen.

### ¿Qué resultó en el examen real (`66` frases, `81` menciones de conceptos)?

* **Precisión — `96,34 %` (meta mínima: `90 %`):** de todas las señas que el sistema decidió mostrar, más de `96` de cada `100` correspondían de verdad a un concepto técnico dicho en clase.
  * Solo se equivocó **`3` veces** mostrando una seña cuando no correspondía: en *"había una **cola** larga afuera de docencia"*, *"dejé una **pila** de pruebas"* y *"se descargó la **pila** del micrófono"*. ¿Por qué? Porque nuestras reglas ya sabían bloquear *"cola de estudiantes"* o *"pila de cuadernos"*, pero no habían visto esas tres frases nuevas del examen.
* **Recuperación — `97,53 %` (meta mínima: `85 %`):** de todas las veces que sí apareció un término del glosario en las frases, el sistema lo detectó casi el `98 %` de las veces.
  * Solo se le escaparon **`2` menciones**: *"una **fuga de memoria**"* y *"la **asignación de memoria**"*. Y el motivo es muy claro para explicarlo: como agregamos una regla que bloquea `"de memoria"` (para que no dispare seña cuando un profe dice *"aprenderse esto de memoria"*), esa misma regla terminó bloqueando sin querer dos términos computacionales válidos que también usan las palabras `"de memoria"`.
* **Términos compuestos (dos palabras como `"lista enlazada"`, `"tabla hash"`, `"árbol binario"`, `"búsqueda binaria"`):** acertó el **`100 %`** (`21` de `21`), sin falsos positivos ni omisiones.

---

## Prueba 3: ¿Aguanta 20 estudiantes mirando la clase al mismo tiempo? (Prueba de carga)

### ¿Cómo se probó?
Durante **5 minutos reales** por escenario, un script simuló estudiantes conectados por WebSocket en tu computador:
* **Escenario A:** `1` sala con `1` emisor y **`20` estudiantes receptores** mirando en vivo.
* **Escenario B:** **`2` salas funcionando al mismo tiempo**, cada una con `1` emisor y `10` estudiantes (`20` receptores en total).

Para aislar el reparto de mensajes sin mezclar el tiempo de transcripción de Whisper, el servidor emitió frases simuladas (`ASR_PROVIDER=stub`) cada `1,5 segundos`. En cada escenario se enviaron `197` frases por sala, es decir, **`3.940` recepciones esperadas** entre todos los estudiantes.

### ¿Qué resultó?
* **Confiabilidad perfecta en local:** **`0` mensajes perdidos**, **`0` duplicados**, **`0` desordenados** y **`0` errores de conexión** en ambos escenarios.
* **Velocidad y consumo del servidor:** los mensajes tardaron **`1 milisegundo`** en lo típico y **`3–4 milisegundos`** en el `95 %` de los envíos. El procesador apenas rondó el **`1,5 %` de uso** (salvo un salto breve inicial a `84 %` al cargar el modelo de lenguaje `spaCy`) usando unos **`338–347 MB` de RAM**.

---

## Resumen rápido: ¿cumplió las metas?

| Aspecto medido | Meta del informe | Lo que obtuvimos | Lectura simple |
|---|---|---|---|
| **Error de transcripción (`WER`)** | `≤ 25 %` | `3,16–3,56 %` (`small` GPU)<br>`8,25–9,45 %` (`base` CPU) | Muy bien: falla ~3 de cada 100 palabras en GPU. |
| **Términos del ramo en el texto** | *(apoyo a RNF03/04)* | `95,7–100 %` con pista vs `80–94,7 %` sin ella | Darle la lista del ramo al ASR es indispensable. |
| **Tiempo de respuesta en servidor** | `p95 ≤ 5.000 ms` | `805–821 ms` (`small` GPU)<br>`1.908–2.251 ms` (`base` CPU) | Cumple con mucha holgura en GPU (`< 0,9 s`). |
| **Precisión / detección de señas** | `≥ 90 %` / `≥ 85 %` | **`96,34 %` / `97,53 %`** | Cumple ambas metas sin hacer trampa en el examen. |
| **Reparto a 20 receptores (1 y 2 salas)** | 0 pérdidas relevantes | **`0` perdidos, `p95 = 3–4 ms`** (`stub`) | El megáfono en memoria reparte sin perder nada. |

---

## Lo que debes aclarar con total honestidad en una defensa (qué NO prueban estos números)

Aunque los resultados son muy positivos para esta etapa, estas pruebas **no** representan todavía un aula real completa por cinco razones claras:

1. **Solo se grabó tu propia voz leyendo un guion:** leer tranquilo produce textos limpios (`3 %` de error). Un profesor hablando de forma espontánea, más rápido, con muletillas o con acentos distintos tendrá un porcentaje de error mayor.
2. **Falta la grabación con ruido o distancia:** las dos grabaciones de ~`6,7` y ~`6,9` minutos que entregaste quedaron ambas cerca del micrófono del teléfono y en silencio. Todavía queda pendiente grabar una prueba en condiciones más difíciles (ruido ambiente de sala o hablando más lejos) para ver cuánto baja la precisión.
3. **La velocidad se midió solo dentro del servidor:** los `~0,8 segundos` en GPU excluyen los `100 ms` iniciales de captura del navegador, el viaje por la red Wi-Fi y lo que demore el celular en mostrar el video.
4. **La prueba de 20 alumnos se hizo con frases simuladas en el mismo PC:** demostró que el reparto WebSocket a 20 conexiones no pierde mensajes ni consume CPU, pero no midió dos salas usando Whisper en GPU exactamente en el mismo segundo ni posibles caídas de señal Wi-Fi real.
5. **No hubo pruebas con estudiantes sordos ni señas reales de PIESDI:** falta validar con usuarios reales (comprensión, cansancio visual con la cola de videos) y completar **SPEC-009** para cerrar permisos por curso, pausa compartida y seguridad antes de probar con personas.
