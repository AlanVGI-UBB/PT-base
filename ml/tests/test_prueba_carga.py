from prueba_carga import RegistroReceptor, analizar_receptor


def test_analizar_receptor_orden_duplicados_perdidos_y_retardo():
    emitidos = [
        {"segment_id": 1, "final": True, "servidor_ms": 1000},
        {"segment_id": 2, "final": True, "servidor_ms": 2000},
        {"segment_id": 3, "final": True, "servidor_ms": 3000},
        {"segment_id": 4, "final": True, "servidor_ms": 4000},
    ]
    # Recibe seg 1, seg 3, seg 2 (fuera de orden!), seg 2 (duplicado!), falta seg 4 (perdido!)
    reg = RegistroReceptor(
        receptor_id="INF-221-1-R01",
        room_id="INF-221-1",
        connected_at_ms=500,
        eventos=[
            {"segment_id": 1, "final": True, "servidor_ms": 1000, "recibido_ms": 1003},
            {"segment_id": 3, "final": True, "servidor_ms": 3000, "recibido_ms": 3007},
            {"segment_id": 2, "final": True, "servidor_ms": 2000, "recibido_ms": 2005},
            {"segment_id": 2, "final": True, "servidor_ms": 2000, "recibido_ms": 2006},
        ],
        finalizada=True,
    )
    res = analizar_receptor(reg, emitidos)
    assert res["esperados"] == 4
    assert res["recibidos"] == 4
    assert res["perdidos"] == 1
    assert res["duplicados"] == 1
    assert res["fuera_de_orden"] == 1
    assert res["retardo_ms"]["min"] == 3.0
    assert res["retardo_ms"]["max"] == 7.0
