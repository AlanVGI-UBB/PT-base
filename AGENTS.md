# AGENTS.md — Instrucciones para sesiones automatizadas

Este archivo guía a cualquier agente/sesión automatizada (opencode, etc.) que trabaje
en este repositorio. Debe respetar las reglas del proyecto.

## Documentación base

- Visión general y ejecución: `README.md`
- Plan técnico de desarrollo (etapas, decisiones de stack): `docs/plan_desarrollo_tecnico.md`
- Decisiones técnicas del prototipo: `docs/decisiones_tecnicas.md`
- Especificaciones que rigen cada entrega: `specs/` (trabajamos a base de specs).
  Cada spec tiene objetivos, alcance, requisitos, criterios de aceptación y verificación.

Antes de implementar nada, leer la spec correspondiente. No introducir código fuera
del alcance declarado en la spec activa.

## Gestores de paquetes

- **Frontend: `pnpm`** (no `npm` ni `yarn`). `package.json` declara `packageManager`.
- **Python: `pip`** sobre `requirements.txt` (sin Poetry/uv por ahora).

## Cómo ejecutar

- Backend: `cd backend && uvicorn app.main:app --reload --port 8000`
- Frontend: `cd frontend && pnpm install && pnpm dev`
- Compose: `docker compose up --build`

## Lint / typecheck / verificación mínima

Ejecutar antes de dar una tarea por terminada:

```powershell
ruff check backend ml
pytest backend/tests
pytest ml/tests
pnpm --prefix frontend build
```

Las pruebas del backend viven en `backend/tests/` (incluyendo una prueba opcional
marcada con `@pytest.mark.modelo` que requiere `pytest backend/tests -m modelo`)
y las pruebas del pipeline de medición en `ml/tests/`.

## Convenciones

- Idioma de documentación y comentarios: español.
- Comentarios en código: solo cuando sean necesarios; no redundar en lo obvio.
- No crear archivos sueltos fuera de la estructura del plan; si se necesita un nuevo
  directorio, justificarlo en una spec.
- No comprometer secretos. `.env` está en `.gitignore`.

## Historial de implementación (REGLA OBLIGATORIA)

Existe un archivo `docs/historial_implementacion.md` que documenta lo que se
implementó en cada commit del proyecto. **Antes de cada `git commit`** (automatizado
o manual) se debe agregar o actualizar la entrada correspondiente en ese archivo,
siguiendo la convención definida al inicio del mismo:

- Encabezado con fecha ISO, hash corto del commit (si ya se conoce) y referencia a
  la spec cubierta (si aplica).
- Resumen del objetivo del commit (1–2 frases).
- Cambios concretos (módulos/archivos nuevos o modificados, comportamiento añadido).
- Verificación ejecutada para darlo por bueno.

Quien haga commit **sin** actualizar `docs/historial_implementacion.md` debe
considerar el commit incompleto y completar la entrada antes de confirmar.

## Plataforma

OS de desarrollo: Windows 11 + PowerShell 5.1. Usar rutas Windows y `venv\Scripts\activate`
(no `source venv/bin/activate`). Para scripts multiplataforma preferir comandos que
funcionen en PowerShell.