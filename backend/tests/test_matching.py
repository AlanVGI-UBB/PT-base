import pytest

from app.glossary.indice import construir_indice
from app.glossary.matching import buscar_terminos


@pytest.fixture
def indice_piloto():
    terminos = [
        {
            "id": 1,
            "curso_id": 1,
            "texto_visible": "lista enlazada",
            "formas": ["lista enlazada", "listas enlazadas", "lista ligada", "listas ligadas"],
            "bloqueos": [],
            "video_url": "/data/videos_senas/lista_enlazada.mp4",
            "estado": "ensayo",
        },
        {
            "id": 2,
            "curso_id": 1,
            "texto_visible": "memoria",
            "formas": ["memoria"],
            "bloqueos": ["de memoria", "mala memoria"],
            "video_url": "/data/videos_senas/memoria.mp4",
            "estado": "ensayo",
        },
        {
            "id": 3,
            "curso_id": 1,
            "texto_visible": "árbol binario",
            "formas": ["árbol binario", "árboles binarios"],
            "bloqueos": [],
            "video_url": "/data/videos_senas/arbol_binario.mp4",
            "estado": "ensayo",
        },
        {
            "id": 4,
            "curso_id": 1,
            "texto_visible": "árbol",
            "formas": ["árbol"],
            "bloqueos": [],
            "video_url": "/data/videos_senas/arbol.mp4",
            "estado": "ensayo",
        },
        {
            "id": 5,
            "curso_id": 1,
            "texto_visible": "recursión",
            "formas": ["recursión", "recursivo", "recursiva"],
            "bloqueos": [],
            "video_url": "/data/videos_senas/recursion.mp4",
            "estado": "ensayo",
        },
        {
            "id": 6,
            "curso_id": 1,
            "texto_visible": "teorema del valor medio",
            "formas": ["teorema del valor medio"],
            "bloqueos": [],
            "video_url": "/data/videos_senas/teorema_vm.mp4",
            "estado": "retirado",
        },
        {
            "id": 7,
            "curso_id": 1,
            "texto_visible": "derivada",
            "formas": ["derivadas"],
            "bloqueos": [],
            "video_url": "/data/videos_senas/derivada.mp4",
            "estado": "ensayo",
        },
    ]
    return construir_indice(terminos)


def test_formas_admitidas_y_texto_detectado(indice_piloto):
    texto = "Usamos Listas Ligadas con una solución recursiva"
    res = buscar_terminos(texto, indice_piloto)
    conceptos = [s["texto_visible"] for s in res.senas]
    detectados = [s["texto_detectado"] for s in res.senas]
    assert conceptos == ["lista enlazada", "recursión"]
    assert detectados == ["Listas Ligadas", "recursiva"]


def test_doble_clave_reconoce_forma_cuando_lema_difiere(indice_piloto):
    # En contexto plural, spaCy lematiza "derivadas" como "derivado",
    # pero la clave de forma "derivadas" debe reconocerla igual.
    res = buscar_terminos("calculamos muchas derivadas parciales", indice_piloto)
    assert len(res.senas) == 1
    assert res.senas[0]["texto_visible"] == "derivada"
    assert res.senas[0]["texto_detectado"] == "derivadas"


def test_bloqueo_consume_palabras_y_registra_abstencion(indice_piloto):
    res = buscar_terminos("apréndanse esto de memoria antes del control", indice_piloto)
    assert res.senas == []
    assert res.abstenciones == [
        {"bloqueo": "de memoria", "texto_detectado": "de memoria"}
    ]


def test_termino_sin_bloqueo_se_activa_normalmente(indice_piloto):
    res = buscar_terminos("reservamos memoria dinámica para el nodo", indice_piloto)
    assert len(res.senas) == 1
    assert res.senas[0]["texto_visible"] == "memoria"
    assert res.senas[0]["texto_detectado"] == "memoria"
    assert res.abstenciones == []


def test_ngrama_mas_largo_antes_de_corto(indice_piloto):
    res = buscar_terminos("recorrimos el árbol binario completo", indice_piloto)
    assert [s["texto_visible"] for s in res.senas] == ["árbol binario"]
    assert [s["texto_detectado"] for s in res.senas] == ["árbol binario"]


def test_termino_retirado_no_se_activa(indice_piloto):
    res = buscar_terminos("el teorema del valor medio es útil", indice_piloto)
    assert res.senas == []
    assert res.abstenciones == []


def test_sin_match(indice_piloto):
    res = buscar_terminos("buenos días a todos los presentes", indice_piloto)
    assert res.senas == []
    assert res.abstenciones == []
