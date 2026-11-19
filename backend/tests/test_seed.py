import json
from pathlib import Path

from app.glossary.indice import construir_indice, limpiar_cache_indices, obtener_indice_curso
from app.glossary.matching import buscar_terminos

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SEED_PATH = DATA_DIR / "seed_glosario.json"
VIDEOS_DIR = DATA_DIR / "videos_senas"


def test_seed_estructura_provisional_y_videos_existen():
    data = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    assert "PROVISIONALES" in data.get("nota", "")
    assert len(data["cursos"]) == 2
    assert data["cursos"][0]["cod_ramo"] == "INF-221"
    assert data["cursos"][1]["cod_ramo"] == "MAT-101"

    terminos_piloto = [t for t in data["terminos"] if t["curso_id"] == 1]
    terminos_control = [t for t in data["terminos"] if t["curso_id"] == 2]
    assert 12 <= len(terminos_piloto) <= 15
    assert len(terminos_control) == 0

    for t in terminos_piloto:
        assert "lema" not in t
        assert "n_palabras" not in t
        assert t["estado"] == "ensayo"
        assert len(t["formas"]) >= 1
        video_path = VIDEOS_DIR / t["video"]
        assert video_path.exists(), f"Falta clip {video_path}"
        assert video_path.stat().st_size > 1024, f"Clip muy pequeño: {video_path}"


def test_seed_indice_sin_ambiguedades_y_formas_en_tres_frases_portadoras():
    data = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    terminos_indice = [
        {
            "id": i + 1,
            "curso_id": t["curso_id"],
            "texto_visible": t["concepto"],
            "formas": t["formas"],
            "bloqueos": t.get("bloqueos", []),
            "video_url": f"/data/videos_senas/{t['video']}",
            "estado": t["estado"],
        }
        for i, t in enumerate(data["terminos"])
    ]
    indice = construir_indice(terminos_indice)

    portadoras = [
        "hoy estudiamos {forma} en el curso",
        "este ejemplo utiliza {forma} aquí",
        "necesitamos repasar {forma} pronto",
    ]
    for t in terminos_indice:
        concepto = t["texto_visible"]
        for forma in t["formas"]:
            for plantilla in portadoras:
                frase = plantilla.format(forma=forma)
                res = buscar_terminos(frase, indice)
                encontrados = [s["texto_visible"] for s in res.senas]
                assert concepto in encontrados, (
                    f"No se reconoció {forma!r} ({concepto}) en {frase!r}; obtuvo {encontrados}"
                )


def test_seed_script_puebla_y_curso_control_queda_vacio(tmp_path, monkeypatch):
    db_path = str(tmp_path / "seed_test.db")
    monkeypatch.setenv("DB_PATH", db_path)

    from app.core.config import get_settings

    get_settings.cache_clear()
    from app.core import db as db_mod

    db_mod._conn = None
    limpiar_cache_indices()

    from scripts.seed_glosario import main as seed_main

    seed_main()
    indice_control = obtener_indice_curso(2)
    assert indice_control.max_ngrama == 0
    assert buscar_terminos("arreglo lista enlazada pila", indice_control).senas == []


def test_generar_clips_no_sobrescribe_sin_forzar(tmp_path, monkeypatch):
    from scripts import generar_clips_ensayo as gen

    seed_fake = tmp_path / "seed.json"
    seed_fake.write_text(
        json.dumps(
            {
                "terminos": [
                    {"concepto": "prueba", "video": "prueba.mp4"},
                ]
            }
        ),
        encoding="utf-8",
    )
    videos_dir = tmp_path / "videos"
    videos_dir.mkdir()
    existente = videos_dir / "prueba.mp4"
    existente.write_bytes(b"clip-real-existente")

    llamado = []
    monkeypatch.setattr(gen, "SEED_PATH", seed_fake)
    monkeypatch.setattr(gen, "VIDEOS_DIR", videos_dir)
    monkeypatch.setattr(gen, "generar_clip", lambda *a, **kw: llamado.append(a))
    monkeypatch.setattr("sys.argv", ["generar_clips_ensayo.py"])

    gen.main()
    assert llamado == []
    assert existente.read_bytes() == b"clip-real-existente"
