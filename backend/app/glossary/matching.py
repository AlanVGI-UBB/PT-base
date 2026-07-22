import spacy

from app.core.nlp import get_nlp

_STOP_POS = {"DET", "ADP", "CCONJ", "SCONJ"}


def buscar_terminos(
    texto: str,
    glosario_por_lema: dict[str, dict],
    max_ngrama: int = 3,
) -> list[dict]:
    nlp: spacy.Language = get_nlp()
    doc = nlp(texto)
    tokens = [
        (t.lemma_.lower(), t.pos_)
        for t in doc
        if t.pos_ not in _STOP_POS and not t.is_punct
    ]
    lemas = [lemma for lemma, _ in tokens]
    encontrados: list[dict] = []
    i = 0
    while i < len(lemas):
        match = None
        for n in range(min(max_ngrama, len(lemas) - i), 0, -1):
            candidato = " ".join(lemas[i : i + n])
            if candidato in glosario_por_lema:
                match = glosario_por_lema[candidato]
                i += n
                break
        if match:
            encontrados.append(match)
        else:
            i += 1
    return encontrados
