from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time
import wave
from collections import Counter
from pathlib import Path
from typing import Any, AsyncIterator

import jiwer
import psutil

ML_DIR = Path(__file__).resolve().parent
if str(ML_DIR) not in sys.path:
    sys.path.insert(0, str(ML_DIR))

from comun import (  # noqa: E402
    BACKEND_DIR,
    RESULTADOS_DIR,
    asegurar_backend_en_path,
    cargar_terminos_seed,
    gpu_memoria_proceso_mb,
    guardar_json_resultado,
    info_gpu,
    recolectar_metadatos,
    resumir_serie,
    sha256_archivo,
)
from normalizacion import normalizar_texto  # noqa: E402

asegurar_backend_en_path()

from app.glossary.indice import Indice, construir_indice  # noqa: E402
from app.glossary.matching import buscar_terminos  # noqa: E402

SAMPLE_RATE_ESPERADO = 16000


def _validar_y_leer_wav(ruta_wav: Path) -> tuple[bytes, int]:
    """Lee un WAV PCM mono 16 kHz s16le y retorna `(pcm_bytes, duracion_ms)`."""
    if not ruta_wav.exists():
        raise FileNotFoundError(f"No existe el archivo de audio: {ruta_wav}")
    with wave.open(str(ruta_wav), "rb") as wf:
        canales = wf.getnchannels()
        ancho = wf.getsampwidth()
        frecuencia = wf.getframerate()
        n_frames = wf.getnframes()
        if canales != 1 or ancho != 2 or frecuencia != SAMPLE_RATE_ESPERADO:
            raise ValueError(
                f"Formato WAV no soportado ({canales} ch, {ancho * 8} bits, {frecuencia} Hz). "
                "Se requiere WAV mono 16 bits PCM 16000 Hz. "
                "Puedes convertirlo con: ffmpeg -i entrada.wav -ar 16000 -ac 1 -sample_fmt s16 salida.wav"
            )
        pcm_bytes = wf.readframes(n_frames)
    duracion_ms = int(round((n_frames * 1000.0) / SAMPLE_RATE_ESPERADO))
    return pcm_bytes, duracion_ms


def calcular_metricas_wer(referencia: str, hipotesis: str) -> dict[str, Any]:
    ref_norm = normalizar_texto(referencia)
    hyp_norm = normalizar_texto(hipotesis)
    if not ref_norm:
        raise ValueError("La transcripción de referencia normalizada está vacía.")
    out = jiwer.process_words(ref_norm, hyp_norm)
    n_palabras = out.hits + out.substitutions + out.deletions
    return {
        "wer": round(float(out.wer), 4),
        "sustituciones": int(out.substitutions),
        "eliminaciones": int(out.deletions),
        "inserciones": int(out.insertions),
        "aciertos": int(out.hits),
        "palabras_referencia": int(n_palabras),
        "referencia_normalizada": ref_norm,
        "hipotesis_normalizada": hyp_norm,
    }


def calcular_cobertura_terminos_en_transcripcion(
    referencia: str,
    hipotesis: str,
    indice: Indice,
) -> dict[str, Any]:
    """Calcula fracción de menciones del glosario en la referencia recuperadas en la transcripción (R7)."""
    ref_res = buscar_terminos(referencia, indice)
    hyp_res = buscar_terminos(hipotesis, indice)

    cnt_ref = Counter(s["texto_visible"] for s in ref_res.senas)
    cnt_hyp = Counter(s["texto_visible"] for s in hyp_res.senas)

    recuperadas_por_concepto = {
        c: min(cnt_ref[c], cnt_hyp[c]) for c in sorted(cnt_ref.keys())
    }
    total_ref = sum(cnt_ref.values())
    total_hyp = sum(cnt_hyp.values())
    total_rec = sum(recuperadas_por_concepto.values())

    return {
        "menciones_referencia": total_ref,
        "menciones_transcripcion": total_hyp,
        "menciones_recuperadas": total_rec,
        "fraccion_recuperada": round(total_rec / total_ref, 4) if total_ref > 0 else None,
        "detalle_por_concepto": {
            c: {
                "referencia": cnt_ref[c],
                "transcripcion": cnt_hyp[c],
                "recuperadas": recuperadas_por_concepto[c],
            }
            for c in sorted(cnt_ref.keys() | cnt_hyp.keys())
        },
    }


def _leer_memoria_proceso_mb(proc: psutil.Process) -> float:
    info = proc.memory_info()
    peak_bytes = max(info.rss, getattr(info, "peak_wset", 0))
    return round(peak_bytes / (1024 * 1024), 2)


async def evaluar_wav_con_provider(
    pcm_bytes: bytes,
    duracion_ms: int,
    referencia_texto: str,
    provider: Any,
    indice: Indice,
    contexto: list[str] | None,
    lang: str = "es",
    trama_ms: int = 100,
    rapido: bool = False,
    device_config: str = "auto",
) -> dict[str, Any]:
    bytes_por_trama = (SAMPLE_RATE_ESPERADO * trama_ms // 1000) * 2
    proc = psutil.Process(os.getpid())
    gpu_antes = info_gpu() if device_config != "cpu" else None
    gpu_max_usada = gpu_antes["vram_usada_mb"] if gpu_antes else None
    proc_gpu_max = gpu_memoria_proceso_mb(os.getpid()) if device_config != "cpu" else None
    mem_proc_max_mb = _leer_memoria_proceso_mb(proc)

    async def _audio_iter() -> AsyncIterator[bytes]:
        t_ini = time.monotonic()
        n_trama = 0
        for offset in range(0, len(pcm_bytes), bytes_por_trama):
            yield pcm_bytes[offset : offset + bytes_por_trama]
            n_trama += 1
            if not rapido:
                objetivo = t_ini + n_trama * (trama_ms / 1000.0)
                restante = objetivo - time.monotonic()
                if restante > 0:
                    await asyncio.sleep(restante)

    segmentos_finales: list[dict[str, Any]] = []
    provisionales_count = 0
    asr_total_ms = 0
    asr_finales_ms = 0

    t0_ns = time.monotonic_ns()
    async for res in provider.transcribe_stream(
        _audio_iter(),
        lang=lang,
        contexto=contexto,
    ):
        asr_total_ms += res.asr_ms
        mem_proc_max_mb = max(mem_proc_max_mb, _leer_memoria_proceso_mb(proc))
        if device_config != "cpu":
            gpu_ahora = info_gpu()
            if gpu_ahora and (gpu_max_usada is None or gpu_ahora["vram_usada_mb"] > gpu_max_usada):
                gpu_max_usada = gpu_ahora["vram_usada_mb"]
            pgpu = gpu_memoria_proceso_mb(os.getpid())
            if pgpu is not None and (proc_gpu_max is None or pgpu > proc_gpu_max):
                proc_gpu_max = pgpu

        if not res.estable:
            provisionales_count += 1
            continue

        asr_finales_ms += res.asr_ms
        nlp_ini_ns = time.monotonic_ns()
        buscar_terminos(res.texto, indice)
        nlp_ms = (time.monotonic_ns() - nlp_ini_ns) // 1_000_000
        emitido_ms = (time.monotonic_ns() - t0_ns) // 1_000_000
        latencia_ms = emitido_ms - res.llegada_fin_ms

        segmentos_finales.append(
            {
                "segmento_id": res.segmento_id,
                "inicio_ms": res.inicio_ms,
                "fin_ms": res.fin_ms,
                "llegada_fin_ms": res.llegada_fin_ms,
                "asr_ms": res.asr_ms,
                "nlp_ms": nlp_ms,
                "emitido_ms": emitido_ms,
                "latencia_servidor_ms": latencia_ms,
                "texto": res.texto,
            }
        )

    wall_ms = (time.monotonic_ns() - t0_ns) // 1_000_000
    mem_proc_max_mb = max(mem_proc_max_mb, _leer_memoria_proceso_mb(proc))

    hipotesis_texto = " ".join(s["texto"] for s in segmentos_finales)
    wer_metricas = calcular_metricas_wer(referencia_texto, hipotesis_texto)
    terminos_res = calcular_cobertura_terminos_en_transcripcion(
        referencia_texto,
        hipotesis_texto,
        indice,
    )

    latencias = [s["latencia_servidor_ms"] for s in segmentos_finales]
    latencia_resumen = resumir_serie(latencias)
    if rapido:
        latencia_resumen["nota"] = "No válida para RNF01: ejecutado con --rapido (sin pacing en tiempo real)."
    else:
        latencia_resumen["excluye"] = (
            "trama de captura en cliente (100 ms), red y renderizado en receptor (R2)"
        )

    rtf_total = round(asr_total_ms / duracion_ms, 4) if duracion_ms > 0 else None
    rtf_finales = round(asr_finales_ms / duracion_ms, 4) if duracion_ms > 0 else None

    memoria_gpu: dict[str, Any] | None = None
    if gpu_antes is not None:
        vram_antes = gpu_antes["vram_usada_mb"]
        delta_mb = (
            max(0, gpu_max_usada - vram_antes)
            if gpu_max_usada is not None
            else None
        )
        memoria_gpu = {
            "proceso_mb": proc_gpu_max,
            "gpu_usada_antes_mb": vram_antes,
            "gpu_usada_max_mb": gpu_max_usada,
            "delta_gpu_mb": delta_mb,
            "vram_total_mb": gpu_antes["vram_total_mb"],
        }

    return {
        "audio_duracion_ms": duracion_ms,
        "wall_clock_ms": wall_ms,
        "modo_rapido": rapido,
        "segmentos_finales": len(segmentos_finales),
        "segmentos_provisionales": provisionales_count,
        "asr_total_ms": asr_total_ms,
        "asr_finales_ms": asr_finales_ms,
        "factor_tiempo_real": rtf_total,
        "factor_tiempo_real_finales": rtf_finales,
        "wer": wer_metricas,
        "terminos_tecnicos": terminos_res,
        "latencia_servidor_ms": latencia_resumen,
        "memoria_proceso_max_mb": mem_proc_max_mb,
        "memoria_gpu": memoria_gpu,
        "meta_rnf": {
            "rnf03_wer_max": 0.25,
            "cumple_rnf03": wer_metricas["wer"] <= 0.25,
            "rnf01_p95_max_ms": 5000,
            "cumple_rnf01_servidor": (
                None
                if rapido or latencia_resumen["p95"] is None
                else latencia_resumen["p95"] <= 5000
            ),
        },
        "transcripcion": hipotesis_texto,
        "segmentos": segmentos_finales,
    }


def _imprimir_resumen(res: dict[str, Any], modelo: str, device: str, prompt: bool, salida: Path) -> None:
    w = res["wer"]
    lat = res["latencia_servidor_ms"]
    term = res["terminos_tecnicos"]
    print(f"=== Evaluación ASR (modelo={modelo}, device={device}, prompt_glosario={prompt}) ===")
    print(f"Duración audio: {res['audio_duracion_ms'] / 1000:.2f} s | Segmentos finales: {res['segmentos_finales']} (provisionales: {res['segmentos_provisionales']})")
    print(
        f"WER={w['wer']:.4f} ({w['wer'] * 100:.2f}%) | "
        f"S={w['sustituciones']} D={w['eliminaciones']} I={w['inserciones']} N={w['palabras_referencia']}"
    )
    print(
        f"Términos del glosario recuperados: {term['menciones_recuperadas']}/{term['menciones_referencia']} "
        f"({term['fraccion_recuperada']})"
    )
    print(f"RTF total (con provisionales): {res['factor_tiempo_real']} | RTF finales: {res['factor_tiempo_real_finales']}")
    print(
        f"Latencia servidor (ms) -> mediana={lat['mediana']} | p95={lat['p95']} | max={lat['max']}"
        + (" [NO VÁLIDA: --rapido]" if res["modo_rapido"] else "")
    )
    print(f"Memoria máxima proceso: {res['memoria_proceso_max_mb']} MB | GPU: {res['memoria_gpu']}")
    print(f"Resultado guardado en: {salida}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evalúa ASR streaming (Segmentador + FasterWhisperProvider) sobre un WAV.")
    parser.add_argument("--audio", type=Path, required=True, help="Archivo WAV mono 16 kHz PCM 16 bits.")
    parser.add_argument("--referencia", type=Path, required=True, help="Archivo TXT con transcripción de referencia.")
    parser.add_argument("--modelo", default="small", help="Modelo Whisper (tiny, base, small, medium...).")
    parser.add_argument("--device", choices=("auto", "cuda", "cpu"), default="auto", help="Dispositivo de inferencia.")
    parser.add_argument("--compute-type", default="auto", help="Precisión CTranslate2 (auto, float16, int8, float32).")
    parser.add_argument(
        "--prompt-glosario",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Activa o desactiva ASR_PROMPT_GLOSARIO.",
    )
    parser.add_argument("--glosario", type=Path, default=BACKEND_DIR / "data" / "seed_glosario.json", help="Glosario semilla.")
    parser.add_argument("--curso-id", type=int, default=1, help="ID del curso piloto en el glosario.")
    parser.add_argument("--lang", default="es", help="Idioma ASR.")
    parser.add_argument("--trama-ms", type=int, default=100, help="Duración de trama PCM en ms (por defecto 100).")
    parser.add_argument("--rapido", action="store_true", help="Alimenta el WAV sin esperar tiempo real (solo válido para WER).")
    parser.add_argument("--salida", type=Path, default=None, help="Ruta opcional para el JSON de salida.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    pcm_bytes, duracion_ms = _validar_y_leer_wav(args.audio)
    referencia_texto = args.referencia.read_text(encoding="utf-8")

    os.environ["WHISPER_MODEL"] = args.modelo
    os.environ["WHISPER_DEVICE"] = args.device
    os.environ["WHISPER_COMPUTE_TYPE"] = args.compute_type
    os.environ["ASR_PROMPT_GLOSARIO"] = "true" if args.prompt_glosario else "false"

    from app.asr.whisper_local import FasterWhisperProvider, _limpiar_cache_modelo
    from app.core.config import get_settings

    get_settings.cache_clear()
    _limpiar_cache_modelo()

    terminos = cargar_terminos_seed(args.glosario, curso_id=args.curso_id)
    indice = construir_indice(terminos)
    terminos_activos = [t for t in terminos if t.get("estado", "ensayo") != "retirado"]
    contexto = [t["texto_visible"] for t in terminos_activos] if args.prompt_glosario else None

    provider = FasterWhisperProvider()
    resultados = asyncio.run(
        evaluar_wav_con_provider(
            pcm_bytes=pcm_bytes,
            duracion_ms=duracion_ms,
            referencia_texto=referencia_texto,
            provider=provider,
            indice=indice,
            contexto=contexto,
            lang=args.lang,
            trama_ms=args.trama_ms,
            rapido=args.rapido,
            device_config=args.device,
        )
    )

    meta = recolectar_metadatos()
    stamp = meta["fecha_utc"][:19].replace(":", "").replace("-", "").replace("T", "_")
    tag_prompt = "prompt" if args.prompt_glosario else "sinprompt"
    salida = args.salida or (
        RESULTADOS_DIR
        / f"asr_{args.audio.stem}_{args.modelo}_{args.device}_{tag_prompt}_{stamp}.json"
    )

    settings = get_settings()
    payload = {
        "tipo": "evaluacion_asr",
        "configuracion": {
            "audio": str(args.audio.as_posix()),
            "audio_sha256": sha256_archivo(args.audio),
            "referencia": str(args.referencia.as_posix()),
            "referencia_sha256": sha256_archivo(args.referencia),
            "glosario": str(args.glosario.as_posix()),
            "glosario_sha256": sha256_archivo(args.glosario),
            "curso_id": args.curso_id,
            "modelo": args.modelo,
            "device": args.device,
            "compute_type": args.compute_type,
            "prompt_glosario": args.prompt_glosario,
            "lang": args.lang,
            "trama_ms": args.trama_ms,
            "asr_silencio_ms": settings.ASR_SILENCIO_MS,
            "asr_max_segmento_ms": settings.ASR_MAX_SEGMENTO_MS,
            "asr_parcial_ms": settings.ASR_PARCIAL_MS,
        },
        "metadatos": meta,
        "resultados": resultados,
    }
    guardar_json_resultado(salida, payload)
    _imprimir_resumen(resultados, args.modelo, args.device, args.prompt_glosario, salida)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
