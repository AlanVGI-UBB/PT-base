from __future__ import annotations

from dataclasses import dataclass, field

from app.core.nlp import get_nlp
from app.glossary.indice import STOP_POS, Indice


@dataclass
class Coincidencias:
    senas: list[dict] = field(default_factory=list)
    abstenciones: list[dict] = field(default_factory=list)


def buscar_terminos(texto: str, indice: Indice) -> Coincidencias:
    if not texto or not texto.strip() or indice.max_ngrama == 0:
        return Coincidencias()

    doc = get_nlp()(texto)
    raw_tokens = [t for t in doc if not t.is_punct and not t.is_space]
    if not raw_tokens:
        return Coincidencias()

    content_tokens = []
    raw_to_content: dict[int, int] = {}
    content_to_raw: list[int] = []
    for k, tok in enumerate(raw_tokens):
        if tok.pos_ not in STOP_POS:
            raw_to_content[k] = len(content_tokens)
            content_tokens.append(tok)
            content_to_raw.append(k)

    senas: list[dict] = []
    abstenciones: list[dict] = []

    k = 0
    total_raw = len(raw_tokens)
    total_content = len(content_tokens)

    while k < total_raw:
        mejor_bloqueo: tuple[int, str] | None = None
        if indice.max_ngrama_bloqueo > 0:
            max_m = min(indice.max_ngrama_bloqueo, total_raw - k)
            for m in range(max_m, 0, -1):
                sub = raw_tokens[k : k + m]
                clave_lema = " ".join(t.lemma_.lower() for t in sub)
                if clave_lema in indice.bloqueos:
                    mejor_bloqueo = (k + m, indice.bloqueos[clave_lema])
                    break
                clave_forma = " ".join(t.text.lower() for t in sub)
                if clave_forma in indice.bloqueos:
                    mejor_bloqueo = (k + m, indice.bloqueos[clave_forma])
                    break

        mejor_forma: tuple[int, dict] | None = None
        if k in raw_to_content:
            f = raw_to_content[k]
            max_n = min(indice.max_ngrama, total_content - f)
            for n in range(max_n, 0, -1):
                sub = content_tokens[f : f + n]
                clave_lema = " ".join(t.lemma_.lower() for t in sub)
                entry = indice.entradas.get(clave_lema)
                if entry is None:
                    clave_forma = " ".join(t.text.lower() for t in sub)
                    entry = indice.entradas.get(clave_forma)
                if entry is not None:
                    fin_raw = content_to_raw[f + n - 1] + 1
                    mejor_forma = (fin_raw, entry)
                    break

        if mejor_bloqueo is not None and (
            mejor_forma is None or mejor_bloqueo[0] > mejor_forma[0]
        ):
            fin_raw, bloqueo_decl = mejor_bloqueo
            tok_ini = raw_tokens[k].i
            tok_fin = raw_tokens[fin_raw - 1].i + 1
            abstenciones.append(
                {
                    "bloqueo": bloqueo_decl,
                    "texto_detectado": doc[tok_ini:tok_fin].text,
                }
            )
            k = fin_raw
        elif mejor_forma is not None:
            fin_raw, entry = mejor_forma
            tok_ini = raw_tokens[k].i
            tok_fin = raw_tokens[fin_raw - 1].i + 1
            senas.append(
                {
                    **entry,
                    "texto_detectado": doc[tok_ini:tok_fin].text,
                }
            )
            k = fin_raw
        else:
            k += 1

    return Coincidencias(senas=senas, abstenciones=abstenciones)
