from datetime import datetime, timezone

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app = FastAPI(title="Puente LSCh API", version="0.1.0")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.websocket("/ws/echo")
async def ws_echo(ws: WebSocket) -> None:
    await ws.accept()
    try:
        while True:
            payload = await ws.receive_text()
            recibido = datetime.now(timezone.utc).isoformat()
            await ws.send_json(
                {
                    "type": "echo",
                    "text": payload,
                    "received_at": recibido,
                    "echoed_at": datetime.now(timezone.utc).isoformat(),
                }
            )
    except WebSocketDisconnect:
        return