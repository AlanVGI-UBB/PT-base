from __future__ import annotations

import hashlib
import importlib.metadata
import json
import math
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psutil

ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
ML_DIR = ROOT_DIR / "ml"
RESULTADOS_DIR = ML_DIR / "resultados"


def asegurar_backend_en_path() -> None:
    """Agrega `backend/` a `sys.path` para importar módulos de `app.*`."""
    backend_str = str(BACKEND_DIR)
    if backend_str not in sys.path:
        sys.path.insert(0, backend_str)


def percentil(valores: list[float | int], p: float) -> float | None:
    """Calcula el percentil `p` (0..100) usando interpolación lineal."""
    if not valores:
        return None
    ordenados = sorted(valores)
    if len(ordenados) == 1:
        return float(ordenados[0])
    pos = (p / 100.0) * (len(ordenados) - 1)
    lo = math.floor(pos)
    hi = math.ceil(pos)
    frac = pos - lo
    return float(ordenados[lo] * (1.0 - frac) + ordenados[hi] * frac)


def resumir_serie(valores: list[float | int]) -> dict[str, float | int | None]:
    """Resume una serie numérica con conteo, mín, mediana, p95, máx y promedio."""
    if not valores:
        return {
            "n": 0,
            "min": None,
            "mediana": None,
            "p95": None,
            "max": None,
            "promedio": None,
        }
    return {
        "n": len(valores),
        "min": round(float(min(valores)), 2),
        "mediana": round(float(percentil(valores, 50) or 0.0), 2),
        "p95": round(float(percentil(valores, 95) or 0.0), 2),
        "max": round(float(max(valores)), 2),
        "promedio": round(float(sum(valores) / len(valores)), 2),
    }


def _git_info() -> dict[str, Any]:
    commit = None
    dirty = None
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=str(ROOT_DIR),
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        status = subprocess.check_output(
            ["git", "status", "--porcelain"],
            cwd=str(ROOT_DIR),
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        dirty = bool(status)
    except Exception:
        pass
    return {"commit": commit, "dirty": dirty}


def info_gpu() -> dict[str, Any] | None:
    """Consulta nombre, memoria total/usada de GPU vía `nvidia-smi`, si existe."""
    try:
        out = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total,memory.used,driver_version",
                "--format=csv,noheader,nounits",
            ],
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=5,
        ).strip()
        if not out:
            return None
        linea = out.splitlines()[0]
        partes = [p.strip() for p in linea.split(",")]
        if len(partes) < 4:
            return None
        return {
            "nombre": partes[0],
            "vram_total_mb": int(float(partes[1])),
            "vram_usada_mb": int(float(partes[2])),
            "driver": partes[3],
        }
    except Exception:
        return None


def gpu_memoria_proceso_mb(pid: int) -> int | None:
    """Retorna VRAM asignada al proceso `pid` en MB vía `nvidia-smi`, o None."""
    try:
        out = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-compute-apps=pid,used_gpu_memory",
                "--format=csv,noheader,nounits",
            ],
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=5,
        )
        total = 0
        encontrado = False
        for linea in out.splitlines():
            partes = [p.strip() for p in linea.split(",")]
            if len(partes) == 2 and partes[0].isdigit() and int(partes[0]) == pid:
                try:
                    total += int(float(partes[1]))
                    encontrado = True
                except ValueError:
                    pass
        return total if encontrado else None
    except Exception:
        return None


def _versiones_paquetes(nombres: list[str]) -> dict[str, str | None]:
    res: dict[str, str | None] = {}
    for nombre in nombres:
        try:
            res[nombre] = importlib.metadata.version(nombre)
        except importlib.metadata.PackageNotFoundError:
            res[nombre] = None
    return res


def recolectar_metadatos(paquetes: list[str] | None = None) -> dict[str, Any]:
    """Construye bloque estándar de trazabilidad para resultados JSON (R16)."""
    pkgs = paquetes or [
        "faster-whisper",
        "ctranslate2",
        "onnxruntime",
        "spacy",
        "es_core_news_md",
        "jiwer",
        "psutil",
        "websockets",
        "fastapi",
        "uvicorn",
        "numpy",
    ]
    mem = psutil.virtual_memory()
    git = _git_info()
    return {
        "fecha_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": git["commit"],
        "git_dirty": git["dirty"],
        "hardware": {
            "plataforma": platform.platform(),
            "procesador": platform.processor() or platform.machine(),
            "python": platform.python_version(),
            "cpu_nucleos_logicos": psutil.cpu_count(logical=True),
            "cpu_nucleos_fisicos": psutil.cpu_count(logical=False),
            "ram_total_mb": round(mem.total / (1024 * 1024), 1),
            "gpu": info_gpu(),
        },
        "versiones": _versiones_paquetes(pkgs),
    }


def sha256_archivo(ruta: Path) -> str:
    h = hashlib.sha256()
    with ruta.open("rb") as fh:
        for bloque in iter(lambda: fh.read(65536), b""):
            h.update(bloque)
    return h.hexdigest()


def cargar_terminos_seed(seed_path: Path, curso_id: int = 1) -> list[dict]:
    """Convierte las entradas de `seed_glosario.json` al formato de `construir_indice`."""
    data = json.loads(seed_path.read_text(encoding="utf-8"))
    terminos: list[dict] = []
    for idx, t in enumerate(data.get("terminos", []), start=1):
        if t["curso_id"] != curso_id:
            continue
        video = t.get("video") or t.get("video_url", "")
        video_url = video if video.startswith("/") else f"/data/videos_senas/{video}"
        terminos.append(
            {
                "id": idx,
                "curso_id": t["curso_id"],
                "texto_visible": t["concepto"],
                "formas": t["formas"],
                "bloqueos": t.get("bloqueos", []),
                "video_url": video_url,
                "estado": t.get("estado", "ensayo"),
            }
        )
    return terminos


def guardar_json_resultado(ruta: Path, payload: dict[str, Any]) -> Path:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return ruta
