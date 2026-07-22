import spacy

_nlp = None


def get_nlp():
    global _nlp
    if _nlp is None:
        from app.core.config import get_settings

        model = get_settings().SPACY_MODEL
        _nlp = spacy.load(model)
    return _nlp
