# Datos de evaluación de la PoC (`ml/datos/`)

## Origen y separación de particiones (`SPEC-008` R11–R12, `RNF04`)

- **`frases_anotadas.jsonl`:** conjunto de 102 frases en español sobre el curso piloto provisional `INF-221` (*Estructuras de Datos*), redactadas por el autor a partir de explicaciones y vocabulario típico de la asignatura (sin grabaciones ni textos de terceros).
  - **Partición `"prueba"` (66 frases):** redactada y congelada el **2026-11-19**, **antes** de definir las formas admitidas y los bloqueos en `backend/data/seed_glosario.json` (`SPEC-007`). No se utiliza para ajustar reglas del glosario ni del motor de coincidencia. Incluye frases sin conceptos, usos cotidianos o ambiguos de palabras del glosario (*"de memoria"*, *"cola larga"*, *"pila de pruebas"*, *"pila del micrófono"*, *"llegamos a un arreglo"*, *"tabla de notas"*), términos compuestos y flexiones.
  - **Partición `"ajuste"` (36 frases):** separada para diseñar y validar reglas, formas y bloqueos durante la implementación de `SPEC-007`.

## Conceptos cubiertos (glosario piloto provisional `INF-221`)

`arreglo`, `lista enlazada`, `pila`, `cola`, `árbol binario`, `nodo`, `puntero`, `grafo`, `tabla hash`, `recursión`, `algoritmo`, `complejidad`, `ordenamiento`, `búsqueda binaria`, `memoria`.
