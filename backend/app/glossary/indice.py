from __future__ import annotations

from dataclasses import dataclass, field

from app.core.config import get_settings
from app.core.nlp import get_nlp
from app.glossary.repository import list_terminos

STOP_POS = {"DET", "ADP", "CCONJ", "SCONJ"}


@dataclass
class Indice:
    entradas: dict[str, dict | None]
    max_ngrama: int
    bloqueos: dict[str, str] = field(default_factory=dict)
    max_ngrama_bloqueo: int = 0


_INDICE_CACHE: dict[tuple[str, int], Indice] = {}


def _claves_expresion(texto: str, filtrar_stop: bool) -> tuple[str, str, int]:
    doc = get_nlp()(texto)
    if filtrar_stop:
        tokens = [
            t
            for t in doc
            if t.pos_ not in STOP_POS and not t.is_punct and not t.is_space
        ]
    else:
        tokens = [t for t in doc if not t.is_punct and not t.is_space]
    clave_lema = " ".join(t.lemma_.lower() for t in tokens)
    clave_forma = " ".join(t.text.lower() for t in tokens)
    return clave_lema, clave_forma, len(tokens)


def construir_indice(terminos: list[dict]) -> Indice:
    entradas: dict[str, dict | None] = {}
    bloqueos_meta: dict[str, str] = {}
    concepto_por_clave: dict[str, str] = {}
    max_ngrama = 0
    max_ngrama_bloqueo = 0

    activos = [t for t in terminos if t.get("estado", "ensayo") != "retirado"]

    for t in activos:
        termino_id = t.get("id") if t.get("id") is not None else t.get("termino_id")
        concepto = t["texto_visible"]
        entry = {
            "termino_id": termino_id,
            "texto_visible": concepto,
            "video_url": t["video_url"],
            "estado": t.get("estado", "ensayo"),
        }
        formas = t.get("formas") or [concepto]
        for forma in formas:
            clave_lema, clave_forma, n = _claves_expresion(forma, filtrar_stop=True)
            if n == 0:
                continue
            max_ngrama = max(max_ngrama, n)
            for clave in (clave_lema, clave_forma):
                if clave in entradas:
                    existente = concepto_por_clave[clave]
                    if existente != concepto:
                        raise ValueError(
                            f"Clave ambigua {clave!r} entre {existente!r} y {concepto!r}"
                        )
                else:
                    entradas[clave] = entry
                    concepto_por_clave[clave] = concepto

    for t in activos:
        for bloqueo in t.get("bloqueos") or []:
            clave_lema, clave_forma, n = _claves_expresion(bloqueo, filtrar_stop=False)
            if n == 0:
                continue
            max_ngrama = max(max_ngrama, n)
            max_ngrama_bloqueo = max(max_ngrama_bloqueo, n)
            for clave in (clave_lema, clave_forma):
                if clave in entradas and entradas[clave] is not None:
                    raise ValueError(
                        f"Bloqueo {bloqueo!r} genera la clave {clave!r}, "
                        f"que colisiona con el concepto {concepto_por_clave[clave]!r}"
                    )
                entradas[clave] = None
                bloqueos_meta[clave] = bloqueo

    return Indice(
        entradas=entradas,
        max_ngrama=max_ngrama,
        bloqueos=bloqueos_meta,
        max_ngrama_bloqueo=max_ngrama_bloqueo,
    )


def obtener_indice_curso(curso_id: int) -> Indice:
    key = (str(get_settings().DB_PATH), curso_id)
    indice = _INDICE_CACHE.get(key)
    if indice is None:
        indice = construir_indice(list_terminos(curso_id))
        _INDICE_CACHE[key] = indice
    return indice


def limpiar_cache_indices(curso_id: int | None = None) -> None:
    if curso_id is None:
        _INDICE_CACHE.clear()
        return
    for key in [k for k in _INDICE_CACHE if k[1] == curso_id]:
        _INDICE_CACHE.pop(key, None)
