import pytest

from app.glossary.matching import buscar_terminos


@pytest.fixture
def glosario():
    return {
        "derivado": {"lema": "derivado", "texto_visible": "derivada", "video_url": "/v/derivada.mp4", "n_palabras": 1},
        "integral": {"lema": "integral", "texto_visible": "integral", "video_url": "/v/integral.mp4", "n_palabras": 1},
        "raíz cuadrado": {"lema": "raíz cuadrado", "texto_visible": "raíz cuadrada", "video_url": "/v/raiz_cuadrada.mp4", "n_palabras": 2},
        "función continuo": {"lema": "función continuo", "texto_visible": "función continua", "video_url": "/v/funcion_continua.mp4", "n_palabras": 2},
        "hablar": {"lema": "hablar", "texto_visible": "hablar", "video_url": "/v/hablar.mp4", "n_palabras": 1},
        "duda": {"lema": "duda", "texto_visible": "duda", "video_url": "/v/duda.mp4", "n_palabras": 1},
    }


def test_ngrama_largo_antes_de_corto(glosario):
    texto = "vamos a calcular la raíz cuadrada de un número"
    encontrados = buscar_terminos(texto, glosario)
    lemas = [e["lema"] for e in encontrados]
    assert "raíz cuadrado" in lemas
    assert "raíz" not in lemas


def test_varios_matches(glosario):
    texto = "la derivada y la integral están relacionadas"
    encontrados = buscar_terminos(texto, glosario)
    lemas = {e["lema"] for e in encontrados}
    assert "derivado" in lemas
    assert "integral" in lemas


def test_flexion_verbo(glosario):
    texto = "mientras él estaba hablando de la derivada"
    encontrados = buscar_terminos(texto, glosario)
    lemas = {e["lema"] for e in encontrados}
    assert "hablar" in lemas
    assert "derivado" in lemas


def test_sin_match(glosario):
    texto = "buenos días a todos"
    encontrados = buscar_terminos(texto, glosario)
    assert len(encontrados) == 0


def test_ngrama_medio(glosario):
    texto = "la función continua es importante"
    encontrados = buscar_terminos(texto, glosario)
    lemas = [e["lema"] for e in encontrados]
    assert "función continuo" in lemas


def test_duda_flexion(glosario):
    texto = "tengo una duda sobre el tema"
    encontrados = buscar_terminos(texto, glosario)
    lemas = {e["lema"] for e in encontrados}
    assert "duda" in lemas
