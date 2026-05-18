# main.py
import argparse
import os
import socket

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from scale import AutoReconnectSerialScale

app = FastAPI()
scale: AutoReconnectSerialScale = None
scale_id: str = ""
args = None


class ScaleStatus(BaseModel):
    scale_id: str
    is_connected: bool
    last_seen: datetime | None = None
    protocol: str | None = None


@app.get("/status", response_model=ScaleStatus)
def get_scale_info():
    return ScaleStatus(
        scale_id=scale.scale_id,
        is_connected=scale.is_connected(),
        last_seen=scale.last_response_time,
        protocol=scale.protocol_version,
    )


@app.get("/ping")
def ping_scale():
    return {"responsive": scale.is_responsive()}


@app.get("/info")
def get_info():
    return {
        "scale_id": scale_id,
        "hostname": socket.gethostname(),
        "port": args.port,
    }


@app.get("/weight")
def read_weight():
    if not scale.is_responsive():
        raise HTTPException(status_code=503, detail="Scale not responsive")
    weight = scale.get_weight()
    if weight is None:
        raise HTTPException(status_code=204, detail="No weight read")
    return {"scale_id": scale_id, "weight": weight}


@app.post("/tare")
def tare_scale():
    if not scale.is_responsive():
        raise HTTPException(status_code=503, detail="Scale not responsive")
    scale.tare()
    return {"scale_id": scale_id, "action": "tared"}


@app.post("/zero")
def zero_scale():
    if not scale.is_responsive():
        raise HTTPException(status_code=503, detail="Scale not responsive")
    scale.zero()
    return {"scale_id": scale_id, "action": "zeroed"}


def entrypoint():
    global scale, scale_id, args

    parser = argparse.ArgumentParser(description="Start a SerialScale FastAPI service")
    parser.add_argument("--port", type=int, default=8000, help="Port to run FastAPI server on")
    parser.add_argument(
        "--device",
        type=str,
        default=os.environ.get("SERIAL_DEVICE"),
        help="Serial port (e.g., /dev/ttyUSB0)",
    )
    parser.add_argument(
        "--scale-id", type=str, default=os.environ.get("SCALE_ID"), help="Unique scale ID or name"
    )
    parser.add_argument("--baudrate", type=int, default=4800, help="Serial baud rate")
    parser.add_argument("--timeout", type=float, default=1.0, help="Serial read timeout")
    args = parser.parse_args()

    scale_id = args.scale_id

    scale = AutoReconnectSerialScale(
        port=args.device,
        baudrate=args.baudrate,
        timeout=args.timeout,
    )

    print(f"Running FastAPI server for scale '{scale_id}' on port {args.port}")
    uvicorn.run("main:app", host="0.0.0.0", port=args.port, reload=False)


if __name__ == "__main__":
    entrypoint()
