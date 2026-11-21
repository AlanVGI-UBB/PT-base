from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ML_DIR = Path(__file__).resolve().parent
if str(ML_DIR) not in sys.path:
    sys.path.insert(0, str(ML_DIR))

from comun import (  # noqa: E402
    BACKEND_DIR,
    RESULTADOS_DIR,
    asegurar_backend_en_path,
    cargar_terminos_seed,
    guardar_json_resultado,
    recolectar_metadatos,
    sha256_archivo,
)

asegurar_backend_en_path()

from app.glossary.indice import construir_indice  # noqa: E402
from app.glossary.matching import buscar_terminos  # noqa: E402


def _metricas_conteos(tp: int, fp: int, fn: int) -> dict[str, Any]:
    precision = round(tp / (tp + fp), 4) if (tp + fp) > 0 else None
    recuperacion = round(tp / (tp + fn), 4) if (tp + fn) > 0 else None
    denom_f1 = 2 * tp + fp + fn
    f1 = round((2 * tp) / denom_f1, 4) if denom_f1 > 0 else None
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "soporte": tp + fn,
        "precision": precision,
        "recuperacion": recuperacion,
        "f1": f1,
    }


def _es_compuesto(concepto: str) -> bool:
    return len(concepto.split()) >= 2


def cargar_frases_jsonl(ruta: Path, particion: str) -> list[tuple[int, dict[str, Any]]]:
    frases: list[tuple[int, dict[str, Any]]] = []
    for n_linea, raw in enumerate(ruta.read_text(encoding="utf-8").splitlines(), start=1):
        linea = raw.strip()
        if not linea:
            continue
        item = json.loads(linea)
        if particion != "todas" and item.get("particion") != particion:
            continue
        frases.append((n_linea, item))
    return frases


def evaluar_matching(
    frases: list[tuple[int, dict[str, Any]]],
    terminos: list[dict[str, Any]],
) -> dict[str, Any]:
    """Evalúa detección de conceptos por frase comparando multiconjuntos (R13, §5.4)."""
    indice = construir_indice(terminos)
    conceptos_cubiertos = sorted(
        {t["texto_visible"] for t in terminos if t.get("estado", "ensayo") != "retirado"}
    )
    set_cubiertos = set(conceptos_cubiertos)

    conteos: dict[str, dict[str, int]] = {
        c: {"tp": 0, "fp": 0, "fn": 0} for c in conceptos_cubiertos
    }
    fuera_glosario: Counter[str] = Counter()
    menciones_cubiertas_total = 0
    errores: list[dict[str, Any]] = []

    for n_linea, item in frases:
        texto = item["texto"]
        esperados_raw = list(item.get("conceptos", []))

        esperados_cubiertos = Counter(c for c in esperados_raw if c in set_cubiertos)
        no_cubiertos = [c for c in esperados_raw if c not in set_cubiertos]
        fuera_glosario.update(no_cubiertos)
        menciones_cubiertas_total += sum(esperados_cubiertos.values())

        res = buscar_terminos(texto, indice)
        detectados = Counter(s["texto_visible"] for s in res.senas)

        fps_frase: list[str] = []
        fns_frase: list[str] = []

        for concepto in sorted(set(esperados_cubiertos.keys()) | set(detectados.keys())):
            det_n = detectados[concepto]
            esp_n = esperados_cubiertos[concepto]
            tp_c = min(det_n, esp_n)
            fp_c = max(0, det_n - esp_n)
            fn_c = max(0, esp_n - det_n)

            bucket = conteos.setdefault(concepto, {"tp": 0, "fp": 0, "fn": 0})
            bucket["tp"] += tp_c
            bucket["fp"] += fp_c
            bucket["fn"] += fn_c

            fps_frase.extend([concepto] * fp_c)
            fns_frase.extend([concepto] * fn_c)

        if fps_frase or fns_frase:
            errores.append(
                {
                    "linea": n_linea,
                    "particion": item.get("particion"),
                    "texto": texto,
                    "esperados_cubiertos": [c for c in esperados_raw if c in set_cubiertos],
                    "esperados_fuera_glosario": no_cubiertos,
                    "detectados": [s["texto_visible"] for s in res.senas],
                    "detalles_senas": [
                        {
                            "concepto": s["texto_visible"],
                            "texto_detectado": s["texto_detectado"],
                        }
                        for s in res.senas
                    ],
                    "abstenciones": res.abstenciones,
                    "falsos_positivos": fps_frase,
                    "falsos_negativos": fns_frase,
                }
            )

    por_concepto: dict[str, Any] = {}
    tot_tp = tot_fp = tot_fn = 0
    comp_tp = comp_fp = comp_fn = 0
    simp_tp = simp_fp = simp_fn = 0

    for concepto in sorted(conteos.keys()):
        tp = conteos[concepto]["tp"]
        fp = conteos[concepto]["fp"]
        fn = conteos[concepto]["fn"]
        es_comp = _es_compuesto(concepto)
        por_concepto[concepto] = {
            "es_compuesto": es_comp,
            **_metricas_conteos(tp, fp, fn),
        }
        tot_tp += tp
        tot_fp += fp
        tot_fn += fn
        if es_comp:
            comp_tp += tp
            comp_fp += fp
            comp_fn += fn
        else:
            simp_tp += tp
            simp_fp += fp
            simp_fn += fn

    menciones_fuera = sum(fuera_glosario.values())
    menciones_totales = menciones_cubiertas_total + menciones_fuera
    tasa_cobertura = (
        round(menciones_cubiertas_total / menciones_totales, 4)
        if menciones_totales > 0
        else None
    )

    global_met = _metricas_conteos(tot_tp, tot_fp, tot_fn)
    meta_rnf04 = {
        "precision_min": 0.90,
        "recuperacion_min": 0.85,
        "cumple_precision": (
            global_met["precision"] is not None and global_met["precision"] >= 0.90
        ),
        "cumple_recuperacion": (
            global_met["recuperacion"] is not None and global_met["recuperacion"] >= 0.85
        ),
    }

    return {
        "total_frases": len(frases),
        "total_errores": len(errores),
        "global": global_met,
        "compuestos": _metricas_conteos(comp_tp, comp_fp, comp_fn),
        "simples": _metricas_conteos(simp_tp, simp_fp, simp_fn),
        "por_concepto": por_concepto,
        "cobertura": {
            "menciones_totales": menciones_totales,
            "menciones_cubiertas": menciones_cubiertas_total,
            "menciones_fuera_glosario": menciones_fuera,
            "tasa_cobertura": tasa_cobertura,
            "conceptos_fuera_glosario": dict(sorted(fuera_glosario.items())),
        },
        "meta_rnf04": meta_rnf04,
        "errores": errores,
    }


def _imprimir_resumen(resultado: dict[str, Any], particion: str, salida: Path) -> None:
    g = resultado["global"]
    c = resultado["compuestos"]
    cob = resultado["cobertura"]
    print(f"=== Evaluación de matching (partición: {particion}) ===")
    print(f"Frases evaluadas: {resultado['total_frases']} | Frases con error: {resultado['total_errores']}")
    print(
        f"Global     -> TP={g['tp']} FP={g['fp']} FN={g['fn']} | "
        f"Precisión={g['precision']} | Recuperación={g['recuperacion']} | F1={g['f1']}"
    )
    print(
        f"Compuestos -> TP={c['tp']} FP={c['fp']} FN={c['fn']} | "
        f"Precisión={c['precision']} | Recuperación={c['recuperacion']} | F1={c['f1']}"
    )
    print(
        f"Cobertura  -> {cob['menciones_cubiertas']}/{cob['menciones_totales']} menciones "
        f"({cob['tasa_cobertura']}); fuera de glosario: {cob['menciones_fuera_glosario']}"
    )
    if resultado["errores"]:
        print("\nErrores detectados:")
        for err in resultado["errores"]:
            print(
                f"  - L{err['linea']}: {err['texto']!r} | "
                f"FP={err['falsos_positivos']} FN={err['falsos_negativos']}"
            )
    print(f"\nResultado guardado en: {salida}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evalúa precisión y recuperación del mapeo de conceptos.")
    parser.add_argument(
        "--datos",
        type=Path,
        default=ML_DIR / "datos" / "frases_anotadas.jsonl",
        help="Ruta al archivo JSONL de frases anotadas.",
    )
    parser.add_argument(
        "--particion",
        choices=("prueba", "ajuste", "todas"),
        default="prueba",
        help="Partición a evaluar.",
    )
    parser.add_argument(
        "--glosario",
        type=Path,
        default=BACKEND_DIR / "data" / "seed_glosario.json",
        help="Ruta al JSON del glosario semilla.",
    )
    parser.add_argument(
        "--curso-id",
        type=int,
        default=1,
        help="ID del curso en el glosario semilla.",
    )
    parser.add_argument(
        "--salida",
        type=Path,
        default=None,
        help="Ruta opcional del JSON de salida.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    frases = cargar_frases_jsonl(args.datos, args.particion)
    if not frases:
        print(f"No se encontraron frases para la partición {args.particion!r} en {args.datos}.", file=sys.stderr)
        return 1

    terminos = cargar_terminos_seed(args.glosario, curso_id=args.curso_id)
    metricas = evaluar_matching(frases, terminos)
    meta = recolectar_metadatos(["spacy", "es_core_news_md", "numpy", "psutil"])

    stamp = meta["fecha_utc"][:19].replace(":", "").replace("-", "").replace("T", "_")
    salida = args.salida or (RESULTADOS_DIR / f"matching_{args.particion}_{stamp}.json")

    payload = {
        "tipo": "evaluacion_matching",
        "configuracion": {
            "datos": str(args.datos.as_posix()),
            "datos_sha256": sha256_archivo(args.datos),
            "particion": args.particion,
            "glosario": str(args.glosario.as_posix()),
            "glosario_sha256": sha256_archivo(args.glosario),
            "curso_id": args.curso_id,
        },
        "metadatos": meta,
        "resultados": metricas,
    }
    guardar_json_resultado(salida, payload)
    _imprimir_resumen(metricas, args.particion, salida)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
