import json

from evaluar_matching import cargar_frases_jsonl, evaluar_matching


def test_evaluar_matching_multiconjunto_compuestos_cobertura_y_errores(tmp_path):
    jsonl = tmp_path / "frases.jsonl"
    filas = [
        {"texto": "insertamos un nodo tras otro nodo", "conceptos": ["nodo", "nodo"], "particion": "prueba"},
        {"texto": "recorremos una lista enlazada y un grafo", "conceptos": ["lista enlazada", "grafo no cubierto"], "particion": "prueba"},
        {"texto": "no se aprendan eso de memoria", "conceptos": [], "particion": "prueba"},
        {"texto": "el algoritmo usa tabla hash", "conceptos": ["lista enlazada"], "particion": "prueba"},
        {"texto": "solo ajuste", "conceptos": ["nodo"], "particion": "ajuste"},
    ]
    jsonl.write_text("\n".join(json.dumps(f, ensure_ascii=False) for f in filas) + "\n", encoding="utf-8")

    frases = cargar_frases_jsonl(jsonl, "prueba")
    assert len(frases) == 4

    terminos = [
        {
            "id": 1,
            "curso_id": 1,
            "texto_visible": "nodo",
            "formas": ["nodo", "nodos"],
            "bloqueos": [],
            "video_url": "/v/nodo.mp4",
            "estado": "ensayo",
        },
        {
            "id": 2,
            "curso_id": 1,
            "texto_visible": "lista enlazada",
            "formas": ["lista enlazada", "listas enlazadas"],
            "bloqueos": [],
            "video_url": "/v/lista.mp4",
            "estado": "ensayo",
        },
        {
            "id": 3,
            "curso_id": 1,
            "texto_visible": "memoria",
            "formas": ["memoria"],
            "bloqueos": ["de memoria"],
            "video_url": "/v/memoria.mp4",
            "estado": "ensayo",
        },
    ]

    res = evaluar_matching(frases, terminos)
    # Linea 1: nodo x2 => 2 TP
    # Linea 2: lista enlazada => 1 TP; "grafo no cubierto" va a cobertura fuera_glosario
    # Linea 3: "de memoria" bloqueado => 0 FP, 0 FN
    # Linea 4: lista enlazada esperada pero no detectada => 1 FN
    assert res["global"]["tp"] == 3
    assert res["global"]["fp"] == 0
    assert res["global"]["fn"] == 1
    assert res["compuestos"]["tp"] == 1
    assert res["compuestos"]["fn"] == 1
    assert res["cobertura"]["menciones_cubiertas"] == 4
    assert res["cobertura"]["menciones_fuera_glosario"] == 1
    assert res["cobertura"]["conceptos_fuera_glosario"] == {"grafo no cubierto": 1}
    assert res["total_errores"] == 1
    assert res["errores"][0]["falsos_negativos"] == ["lista enlazada"]
