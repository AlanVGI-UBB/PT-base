# Carpeta `specs/`

Esta carpeta contiene las **especificaciones técnicas** (specs) que rigen el desarrollo del proyecto **Puente LSCh**.

## Filosofía de trabajo

1. **Spec → Implementación → Verificación.** Cada pieza del sistema se diseña primero como una spec en este directorio. Solo se comienza a implementar cuando la spec está aprobada.
2. **Una spec = una unidad entregable.** Cada spec debe ser lo bastante acotada para poder implementarse y verificarse de forma independiente en pocos días.
3. **Las specs viven con el código.** Se versionan junto al repositorio y se actualizan si el desarrollo revela supuestos incorrectos. Cuando una spec cambia de forma significativa, se deja nota del cambio al final del archivo.

## Convenciones

- **Nombrado:** `SPEC-NNN-slug-descriptivo.md`, donde `NNN` es un número secuencial de tres dígitos (ej. `SPEC-001`, `SPEC-002`).
- **Idioma:** español, mismo lenguaje del resto de la documentación del proyecto.
- **Alcance:** cada spec se mapea a una o varias etapas de `docs/plan_desarrollo_tecnico.md` y debe referenciarlas explícitamente.

## Estructura sugerida de una spec

```markdown
# SPEC-NNN — <Título>

**Etapa del plan:** <referencia a `docs/plan_desarrollo_tecnico.md`>
**Estado:** Borrador | Aprobada | En implementación | Completada
**Depende de:** <otras specs, o "—" si es inicial>

## 1. Objetivo
Qué se busca lograr con esta spec, en una o dos frases.

## 2. Contexto y supuestos
Premisas técnicas, restricciones, decisiones ya tomadas que afectan esta spec.

## 3. Alcance
### Incluido
### Explícitamente fuera

## 4. Requisitos
Lista numerada de requisitos concretos y verificables. Cada requisito debe poder
responder "sí/no" durante la verificación.

## 5. Diseño técnico
Estructura de archivos, componentes, interfaces, esquemas de datos, flujos.

## 6. Criterios de aceptación
Condiciones objetivas que se deben cumplir para dar la spec por completada.

## 7. Tareas de implementación
Checklist ordenado de tareas.

## 8. Verificación
Comandos/procedimientos para validar la implementación.

## 9. Notas / decisiones diferidas
```

## Índice de specs

| ID  | Título | Estado |
|-----|--------|--------|
| SPEC-001 | Fundación del proyecto (scaffold + hello world WebSocket) | Completada |
| SPEC-002 | Backend del flujo profesor→alumno (ASR + glosario + matching + logging mínimo) | Completada |
| SPEC-003 | PWA: vistas profesor y alumno + captura de audio + reproducción de señas | Completada |
| SPEC-004 | Perfil único centrado en el estudiante + sesiones en vivo con fan-out + historial con replay | Completada |
| SPEC-005 | Mejoras de UX: feedback de conexión, reproducción de señas y errores visibles | Completada |
| SPEC-006 | Transcripción real: captura PCM en el navegador + faster-whisper local | Completada |
| SPEC-007 | Glosario del curso piloto provisional, clips de ensayo y motor de coincidencia | Completada |
| SPEC-008 | Mediciones de la prueba de concepto: transcripción, coincidencia y distribución | Completada (brecha acústica R9 declarada) |
| SPEC-009 | Acceso por inscripción, permiso de captura, estado de sesión y saneamiento | Borrador |

### Cierre del anteproyecto (SPEC-006 a SPEC-009)

Estas cuatro specs salen de la revisión del prototipo contra la propuesta aprobada y el informe de avance (2026-11-16).

- **Orden recomendado:** 006 → 007 → 008 → 009. La numeración sigue ese orden.
- **Dependencias:** 007 necesita el manejo de texto final de 006; 008 mide lo que construyen 006 y 007; 009 solo depende de 007 para la protección de los clips.
- **Una excepción al orden:** las frases de prueba de SPEC-008 (R11 y R12) se redactan antes de ajustar las formas y los bloqueos de SPEC-007.
- **Si el tiempo no alcanza:** 009 se puede reducir a su mínimo (R1–R5 y R21–R23, ver su §9).
- **Lo que ninguna spec resuelve:** la selección del curso piloto, el co-diseño con intérpretes de PIESDI y la grabación y validación del banco de señas (OE1, actividades 1 a 3 del anteproyecto). No son tareas de software.