import pytest

from app.glossary.indice import construir_indice
from app.glossary.matching import buscar_terminos


def test_construir_indice_omite_retirados_y_calcula_max_ngrama():
    terminos = [
        {
            "id": 1,
            "texto_visible": "estructura lineal enlazada simple",
            "formas": ["estructura lineal enlazada simple"],
            "bloqueos": [],
            "video_url": "/v/1.mp4",
            "estado": "ensayo",
        },
        {
            "id": 2,
            "texto_visible": "obsoleto",
            "formas": ["obsoleto"],
            "bloqueos": [],
            "video_url": "/v/2.mp4",
            "estado": "retirado",
        },
    ]
    indice = construir_indice(terminos)
    assert indice.max_ngrama == 4
    assert "obsoleto" not in indice.entradas

    res = buscar_terminos("vemos una estructura lineal enlazada simple hoy", indice)
    assert len(res.senas) == 1
    assert res.senas[0]["texto_detectado"] == "estructura lineal enlazada simple"


def test_construir_indice_rechaza_claves_ambiguas_nombrando_ambos_conceptos():
    terminos = [
        {
            "id": 1,
            "texto_visible": "pila",
            "formas": ["pila", "stack"],
            "bloqueos": [],
            "video_url": "/v/pila.mp4",
            "estado": "ensayo",
        },
        {
            "id": 2,
            "texto_visible": "cola",
            "formas": ["cola", "stack"],
            "bloqueos": [],
            "video_url": "/v/cola.mp4",
            "estado": "ensayo",
        },
    ]
    with pytest.raises(ValueError) as exc:
        construir_indice(terminos)
    msg = str(exc.value)
    assert "pila" in msg
    assert "cola" in msg


def test_construir_indice_rechaza_bloqueo_que_colisiona_sin_ser_mas_largo():
    terminos = [
        {
            "id": 1,
            "texto_visible": "memoria",
            "formas": ["memoria"],
            "bloqueos": ["memoria"],
            "video_url": "/v/memoria.mp4",
            "estado": "ensayo",
        }
    ]
    with pytest.raises(ValueError):
        construir_indice(terminos)


def test_construir_indice_filtra_stopwords_en_formas_y_conserva_en_bloqueos():
    terminos = [
        {
            "id": 1,
            "texto_visible": "memoria",
            "formas": ["memoria"],
            "bloqueos": ["de memoria"],
            "video_url": "/v/memoria.mp4",
            "estado": "ensayo",
        }
    ]
    indice = construir_indice(terminos)
    assert indice.entradas["memoria"] is not None
    assert "de memoria" in indice.bloqueos
    assert indice.entradas["de memoria"] is None
