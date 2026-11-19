import argparse
import json
import subprocess
import tempfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SEED_PATH = BASE_DIR / "data" / "seed_glosario.json"
VIDEOS_DIR = BASE_DIR / "data" / "videos_senas"

FUENTES_POR_DEFECTO = [
    Path("C:/Windows/Fonts/arial.ttf"),
    Path("C:/Windows/Fonts/segoeui.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
]


def _resolver_fuente(fuente_arg: str | None) -> Path:
    if fuente_arg:
        ruta = Path(fuente_arg)
        if not ruta.exists():
            raise FileNotFoundError(f"No existe la tipografía indicada: {ruta}")
        return ruta
    for candidata in FUENTES_POR_DEFECTO:
        if candidata.exists():
            return candidata
    raise FileNotFoundError(
        "No se encontró una tipografía del sistema. Pasa la ruta con --fuente."
    )


def _escapar_ruta_ffmpeg(ruta: Path) -> str:
    return ruta.resolve().as_posix().replace(":", "\\:")


def generar_clip(concepto: str, destino: Path, fuente: Path) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    fuente_esc = _escapar_ruta_ffmpeg(fuente)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        f_titulo = tmp_dir / "titulo.txt"
        f_concepto = tmp_dir / "concepto.txt"
        f_nota = tmp_dir / "nota.txt"
        f_titulo.write_text("CLIP DE ENSAYO", encoding="utf-8")
        f_concepto.write_text(concepto.upper(), encoding="utf-8")
        f_nota.write_text("Sin validación lingüística", encoding="utf-8")

        vf = ",".join(
            [
                f"drawtext=fontfile='{fuente_esc}':textfile='{_escapar_ruta_ffmpeg(f_titulo)}'"
                ":fontcolor=#58a6ff:fontsize=22:x=(w-text_w)/2:y=95",
                f"drawtext=fontfile='{fuente_esc}':textfile='{_escapar_ruta_ffmpeg(f_concepto)}'"
                ":fontcolor=#f0f6fc:fontsize=40:x=(w-text_w)/2:y=(h-text_h)/2",
                f"drawtext=fontfile='{fuente_esc}':textfile='{_escapar_ruta_ffmpeg(f_nota)}'"
                ":fontcolor=#8b949e:fontsize=18:x=(w-text_w)/2:y=245",
            ]
        )

        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=#0d1117:s=640x360:d=3:r=30",
            "-vf",
            vf,
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            "-an",
            str(destino),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(
                f"Error generando {destino.name} con ffmpeg: {res.stderr.strip()}"
            )


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera clips MP4 de ensayo sin personas.")
    parser.add_argument("--fuente", help="Ruta al archivo .ttf/.otf para ffmpeg drawtext")
    parser.add_argument(
        "--forzar",
        action="store_true",
        help="Sobrescribe clips existentes en data/videos_senas/",
    )
    args = parser.parse_args()

    fuente = _resolver_fuente(args.fuente)
    data = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    VIDEOS_DIR.mkdir(parents=True, exist_ok=True)

    generados = 0
    omitidos = 0
    vistos: set[str] = set()

    for t in data["terminos"]:
        video = Path(t["video"]).name
        if video in vistos:
            continue
        vistos.add(video)
        destino = VIDEOS_DIR / video
        if destino.exists() and not args.forzar:
            omitidos += 1
            continue
        generar_clip(t["concepto"], destino, fuente)
        generados += 1

    print(f"Clips de ensayo: {generados} generados, {omitidos} omitidos (existentes).")


if __name__ == "__main__":
    main()
