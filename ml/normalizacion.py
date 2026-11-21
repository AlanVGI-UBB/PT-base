from __future__ import annotations

import unicodedata


def normalizar_texto(texto: str) -> str:
    """Normaliza texto previa al WER: NFC, minúsculas y sin puntuación."""
    if not texto:
        return ""
    nfc = unicodedata.normalize("NFC", texto).lower()
    caracteres = [
        " " if unicodedata.category(ch).startswith("P") else ch
        for ch in nfc
    ]
    return " ".join("".join(caracteres).split())
