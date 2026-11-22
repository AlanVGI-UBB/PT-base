from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import wave
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import psutil
import websockets

ML_DIR = Path(__file__).resolve().parent
if str(ML_DIR) not in sys.path:
    sys.path.insert(0, str(ML_DIR))

from comun import (  # noqa: E402
    RESULTADOS_DIR,
    guardar_json_resultado,
    recolectar_metadatos,
    resumir_serie,
)

SAMPLE_RATE = 16000
TRAMA_MS = 100
MUESTRAS_TRAMA = SAMPLE_RATE * TRAMA_MS // 1000
TRAMA_SILENCIO = b"\x00\x00" * MUESTRAS_TRAMA

ESCENARIOS: dict[str, list[tuple[str, int]]] = {
    "A": [("INF-221-1", 20)],
    "B": [("INF-221-1", 10), ("MAT-101-3", 10)],
}


@dataclass
class RegistroReceptor:
    receptor_id: str
    room_id: str
    connected_at_ms: int = 0
    eventos: list[dict[str, Any]] = field(default_factory=list)
    finalizada: bool = False
    error: str | None = None


def analizar_receptor(
    rec: RegistroReceptor,
    emitidos_sala: list[dict[str, Any]],
) -> dict[str, Any]:
    """Calcula recibidos, perdidos, duplicados, fuera de orden y retardo de un receptor (R14)."""
    esperados_seq = [
        (ev["segment_id"], bool(ev["final"]))
        for ev in emitidos_sala
        if ev["servidor_ms"] >= rec.connected_at_ms
    ]
    pos_esperado: dict[tuple[int, bool], int] = {}
    for idx, clave in enumerate(esperados_seq):
        pos_esperado.setdefault(clave, idx)

    recibidos_seq = [(ev["segment_id"], bool(ev["final"])) for ev in rec.eventos]
    cnt_rec = Counter(recibidos_seq)
    cnt_esp = Counter(esperados_seq)

    duplicados = sum(max(0, c - 1) for c in cnt_rec.values())
    perdidos = sum(max(0, cnt_esp[k] - cnt_rec[k]) for k in cnt_esp)

    fuera_de_orden = 0
    max_idx = -1
    vistos: set[tuple[int, bool]] = set()
    for clave in recibidos_seq:
        if clave in vistos or clave not in pos_esperado:
            continue
        vistos.add(clave)
        idx = pos_esperado[clave]
        if idx < max_idx:
            fuera_de_orden += 1
        else:
            max_idx = idx

    retardos = [
        ev["recibido_ms"] - ev["servidor_ms"]
        for ev in rec.eventos
        if ev.get("servidor_ms") is not None
    ]

    return {
        "receptor_id": rec.receptor_id,
        "room_id": rec.room_id,
        "esperados": len(esperados_seq),
        "recibidos": len(recibidos_seq),
        "perdidos": perdidos,
        "duplicados": duplicados,
        "fuera_de_orden": fuera_de_orden,
        "finalizada": rec.finalizada,
        "error": rec.error,
        "retardo_ms": resumir_serie(retardos),
    }


def _cargar_tramas_wav(ruta_wav: Path) -> list[bytes]:
    with wave.open(str(ruta_wav), "rb") as wf:
        if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getframerate() != SAMPLE_RATE:
            raise ValueError("El WAV opcional debe ser PCM mono 16 bits 16000 Hz")
        raw = wf.readframes(wf.getnframes())
    bytes_trama = MUESTRAS_TRAMA * 2
    return [
        raw[i : i + bytes_trama]
        for i in range(0, len(raw), bytes_trama)
        if i + bytes_trama <= len(raw)
    ]


def _http_json(url: str, data: dict[str, Any] | None = None, token: str | None = None) -> dict[str, Any]:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method="POST" if data is not None else "GET")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def obtener_token(url_http: str, rut: str, password: str) -> str:
    resp = _http_json(f"{url_http.rstrip('/')}/api/auth/login", {"rut": rut, "password": password})
    return resp.get("token") or resp["access_token"]


def detectar_pid_servidor(url_http: str) -> int | None:
    parsed = urllib.parse.urlparse(url_http)
    puerto = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        for conn in psutil.net_connections(kind="inet"):
            if conn.status == psutil.CONN_LISTEN and conn.laddr and conn.laddr.port == puerto and conn.pid:
                return conn.pid
    except Exception:
        pass
    for proc in psutil.process_iter(["pid"]):
        try:
            for conn in proc.net_connections(kind="inet"):
                if conn.status == psutil.CONN_LISTEN and conn.laddr and conn.laddr.port == puerto:
                    return proc.pid
        except Exception:
            continue
    return None


async def _esperar_sala_activa(url_http: str, room_id: str, token: str, timeout_s: float = 5.0) -> None:
    fin = time.monotonic() + timeout_s
    url = f"{url_http.rstrip('/')}/api/salas/{room_id}/estado"
    while time.monotonic() < fin:
        try:
            estado = await asyncio.to_thread(_http_json, url, None, token)
            if estado.get("activa"):
                return
        except urllib.error.URLError:
            pass
        await asyncio.sleep(0.05)
    raise TimeoutError(f"La sala {room_id} no quedó activa en {timeout_s} s")


async def _ejecutar_receptor(
    ws_url: str,
    reg: RegistroReceptor,
    conectado_ev: asyncio.Event,
) -> None:
    try:
        async with websockets.connect(ws_url, max_size=2**20) as ws:
            reg.connected_at_ms = time.time_ns() // 1_000_000
            conectado_ev.set()
            async for raw in ws:
                ahora_ms = time.time_ns() // 1_000_000
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                tipo = data.get("type")
                if tipo == "segmento":
                    reg.eventos.append(
                        {
                            "segment_id": data["segment_id"],
                            "final": bool(data.get("final", True)),
                            "servidor_ms": data.get("servidor_ms"),
                            "recibido_ms": ahora_ms,
                        }
                    )
                elif tipo == "clase_finalizada":
                    reg.finalizada = True
                    break
                elif tipo == "error":
                    reg.error = data.get("mensaje", "error desconocido")
                    break
    except Exception as exc:
        reg.error = str(exc)
        conectado_ev.set()


async def _ejecutar_sala(
    room_id: str,
    n_receptores: int,
    duracion_s: float,
    url_http: str,
    url_ws: str,
    token: str,
    escenario: str,
    tramas_wav: list[bytes] | None,
) -> dict[str, Any]:
    tok_q = urllib.parse.quote(token, safe="")
    ws_em = f"{url_ws.rstrip('/')}/ws/sala/{room_id}?rol=emitter&token={tok_q}&condiciones=1"
    ws_lis = f"{url_ws.rstrip('/')}/ws/sala/{room_id}?rol=listener&token={tok_q}"

    emitidos_sala: list[dict[str, Any]] = []
    emisor_terminado = asyncio.Event()
    registros: list[RegistroReceptor] = []
    receptor_tasks: list[asyncio.Task] = []

    async with websockets.connect(ws_em, max_size=2**20) as em_ws:
        async def _leer_emisor() -> None:
            try:
                async for raw in em_ws:
                    data = json.loads(raw)
                    if data.get("type") == "segmento":
                        emitidos_sala.append(
                            {
                                "segment_id": data["segment_id"],
                                "final": bool(data.get("final", True)),
                                "servidor_ms": data.get("servidor_ms"),
                            }
                        )
                    elif data.get("type") == "clase_finalizada":
                        break
            except Exception:
                pass
            finally:
                emisor_terminado.set()

        reader_em_task = asyncio.create_task(_leer_emisor())
        await _esperar_sala_activa(url_http, room_id, token)

        ready_events: list[asyncio.Event] = []
        for idx in range(n_receptores):
            reg = RegistroReceptor(receptor_id=f"{room_id}-R{idx + 1:02d}", room_id=room_id)
            ev = asyncio.Event()
            registros.append(reg)
            ready_events.append(ev)
            receptor_tasks.append(asyncio.create_task(_ejecutar_receptor(ws_lis, reg, ev)))

        await asyncio.gather(*(ev.wait() for ev in ready_events))

        t_ini = time.monotonic()
        t_fin = t_ini + duracion_s
        trama_idx = 0
        while time.monotonic() < t_fin and not emisor_terminado.is_set():
            if tramas_wav:
                frame = tramas_wav[trama_idx % len(tramas_wav)]
            else:
                frame = TRAMA_SILENCIO
            await em_ws.send(frame)
            trama_idx += 1
            objetivo = t_ini + trama_idx * (TRAMA_MS / 1000.0)
            restante = objetivo - time.monotonic()
            if restante > 0:
                await asyncio.sleep(min(restante, max(0.0, t_fin - time.monotonic())))

        await em_ws.send(json.dumps({"action": "finalizar", "titulo": f"Carga {escenario} {room_id}"}))
        await asyncio.gather(*receptor_tasks, return_exceptions=True)
        try:
            await asyncio.wait_for(reader_em_task, timeout=10.0)
        except asyncio.TimeoutError:
            reader_em_task.cancel()

    por_receptor = [analizar_receptor(reg, emitidos_sala) for reg in registros]
    todos_retardos = [
        ev["recibido_ms"] - ev["servidor_ms"]
        for reg in registros
        for ev in reg.eventos
        if ev.get("servidor_ms") is not None
    ]

    return {
        "room_id": room_id,
        "receptores_configurados": n_receptores,
        "eventos_emitidos_sala": len(emitidos_sala),
        "recibidos_total": sum(r["recibidos"] for r in por_receptor),
        "perdidos_total": sum(r["perdidos"] for r in por_receptor),
        "duplicados_total": sum(r["duplicados"] for r in por_receptor),
        "fuera_de_orden_total": sum(r["fuera_de_orden"] for r in por_receptor),
        "receptores_con_error": sum(1 for r in por_receptor if r["error"] is not None),
        "retardo_global_ms": resumir_serie(todos_retardos),
        "por_receptor": por_receptor,
    }


async def _muestrear_servidor(pid: int | None, stop_event: asyncio.Event) -> dict[str, Any]:
    if pid is None:
        return {"pid": None, "nota": "PID de servidor no detectado", "cpu_pct": resumir_serie([]), "rss_mb": resumir_serie([])}
    try:
        proc = psutil.Process(pid)
        proc.cpu_percent(interval=None)
    except Exception as exc:
        return {"pid": pid, "nota": f"No se pudo inspeccionar PID {pid}: {exc}", "cpu_pct": resumir_serie([]), "rss_mb": resumir_serie([])}

    cpus: list[float] = []
    rss_mbs: list[float] = []
    while not stop_event.is_set():
        await asyncio.sleep(1.0)
        try:
            cpus.append(proc.cpu_percent(interval=None))
            rss_mbs.append(proc.memory_info().rss / (1024 * 1024))
        except psutil.NoSuchProcess:
            break

    return {
        "pid": pid,
        "muestras": len(cpus),
        "cpu_pct": resumir_serie(cpus),
        "rss_mb": resumir_serie(rss_mbs),
    }


async def ejecutar_prueba_carga(
    escenario: str,
    minutos: float,
    url_http: str,
    url_ws: str,
    rut: str,
    password: str,
    pid: int | None,
    wav_path: Path | None,
) -> dict[str, Any]:
    salas_cfg = ESCENARIOS[escenario]
    tramas_wav = _cargar_tramas_wav(wav_path) if wav_path else None
    token = await asyncio.to_thread(obtener_token, url_http, rut, password)
    pid_srv = pid if pid is not None else detectar_pid_servidor(url_http)

    duracion_s = minutos * 60.0
    stop_sample = asyncio.Event()
    sampler_task = asyncio.create_task(_muestrear_servidor(pid_srv, stop_sample))

    t0 = time.monotonic()
    salas_res = await asyncio.gather(
        *(
            _ejecutar_sala(
                room_id=room_id,
                n_receptores=n_rec,
                duracion_s=duracion_s,
                url_http=url_http,
                url_ws=url_ws,
                token=token,
                escenario=escenario,
                tramas_wav=tramas_wav,
            )
            for room_id, n_rec in salas_cfg
        )
    )
    duracion_real_s = round(time.monotonic() - t0, 2)
    stop_sample.set()
    servidor_res = await sampler_task

    perdidos_tot = sum(s["perdidos_total"] for s in salas_res)
    duplicados_tot = sum(s["duplicados_total"] for s in salas_res)
    fuera_tot = sum(s["fuera_de_orden_total"] for s in salas_res)
    recibidos_tot = sum(s["recibidos_total"] for s in salas_res)
    errores_tot = sum(s["receptores_con_error"] for s in salas_res)
    retardos_p95_salas = [
        s["retardo_global_ms"]["p95"]
        for s in salas_res
        if s["retardo_global_ms"]["p95"] is not None
    ]

    return {
        "escenario": escenario,
        "duracion_objetivo_min": minutos,
        "duracion_real_s": duracion_real_s,
        "salas": salas_res,
        "resumen_global": {
            "salas": len(salas_res),
            "receptores_totales": sum(s["receptores_configurados"] for s in salas_res),
            "recibidos_total": recibidos_tot,
            "perdidos_total": perdidos_tot,
            "duplicados_total": duplicados_tot,
            "fuera_de_orden_total": fuera_tot,
            "receptores_con_error": errores_tot,
            "retardo_p95_max_salas_ms": max(retardos_p95_salas) if retardos_p95_salas else None,
        },
        "servidor": servidor_res,
        "meta_rnf06": {
            "descripcion": "Una fuente + 20 receptores (A), dos fuentes + 10 receptores c/u (B)",
            "sin_perdidas_ni_errores": perdidos_tot == 0 and errores_tot == 0,
        },
    }


def _imprimir_resumen(res: dict[str, Any], salida: Path) -> None:
    rg = res["resumen_global"]
    srv = res["servidor"]
    print(f"=== Prueba de carga — Escenario {res['escenario']} ({res['duracion_real_s']} s) ===")
    print(
        f"Global -> receptores={rg['receptores_totales']} | recibidos={rg['recibidos_total']} | "
        f"perdidos={rg['perdidos_total']} | duplicados={rg['duplicados_total']} | "
        f"fuera_orden={rg['fuera_de_orden_total']} | errores={rg['receptores_con_error']}"
    )
    for sala in res["salas"]:
        ret = sala["retardo_global_ms"]
        print(
            f"  Sala {sala['room_id']} ({sala['receptores_configurados']} rec): "
            f"emitidos={sala['eventos_emitidos_sala']} rec_tot={sala['recibidos_total']} "
            f"perd={sala['perdidos_total']} | retardo ms mediana={ret['mediana']} p95={ret['p95']} max={ret['max']}"
        )
    print(
        f"Servidor (PID={srv['pid']}): CPU% mediana={srv['cpu_pct']['mediana']} max={srv['cpu_pct']['max']} | "
        f"RSS MB mediana={srv['rss_mb']['mediana']} max={srv['rss_mb']['max']}"
    )
    print(f"Resultado guardado en: {salida}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ejecuta prueba de carga de distribución WebSocket (R14).")
    parser.add_argument("--escenario", choices=("A", "B"), required=True, help="A: 1 sala (1+20); B: 2 salas (1+10 c/u).")
    parser.add_argument("--minutos", type=float, default=5.0, help="Duración en minutos (por defecto 5).")
    parser.add_argument("--url-http", default="http://127.0.0.1:8000", help="URL base HTTP del backend.")
    parser.add_argument("--url-ws", default="ws://127.0.0.1:8000", help="URL base WebSocket del backend.")
    parser.add_argument("--rut", default="12345678-5", help="RUT del usuario de prueba.")
    parser.add_argument("--password", default="test123", help="Contraseña del usuario de prueba.")
    parser.add_argument("--pid", type=int, default=None, help="PID del proceso servidor para monitorear con psutil.")
    parser.add_argument("--wav", type=Path, default=None, help="WAV opcional (16kHz mono s16le) si backend usa whisper.")
    parser.add_argument("--salida", type=Path, default=None, help="Ruta opcional del JSON de salida.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    resultados = asyncio.run(
        ejecutar_prueba_carga(
            escenario=args.escenario,
            minutos=args.minutos,
            url_http=args.url_http,
            url_ws=args.url_ws,
            rut=args.rut,
            password=args.password,
            pid=args.pid,
            wav_path=args.wav,
        )
    )
    meta = recolectar_metadatos(["fastapi", "uvicorn", "websockets", "psutil", "numpy"])
    stamp = meta["fecha_utc"][:19].replace(":", "").replace("-", "").replace("T", "_")
    modo = "whisper" if args.wav else "stub"
    salida = args.salida or (
        RESULTADOS_DIR / f"carga_escenario_{args.escenario}_{modo}_{stamp}.json"
    )
    payload = {
        "tipo": "prueba_carga",
        "configuracion": {
            "escenario": args.escenario,
            "salas": [
                {"room_id": r, "receptores": n} for r, n in ESCENARIOS[args.escenario]
            ],
            "minutos": args.minutos,
            "url_http": args.url_http,
            "url_ws": args.url_ws,
            "modo_audio": modo,
            "wav": str(args.wav.as_posix()) if args.wav else None,
        },
        "metadatos": meta,
        "resultados": resultados,
    }
    guardar_json_resultado(salida, payload)
    _imprimir_resumen(resultados, salida)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
