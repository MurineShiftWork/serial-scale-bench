import argparse
import socket

import uvicorn
from fastapi import FastAPI, HTTPException
from scale import SerialScale

app = FastAPI()
scale: SerialScale = None
scale_id: str = ""


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
        "--device", type=str, required=True, help="Serial port (e.g., /dev/ttyUSB0)"
    )
    parser.add_argument("--scale-id", type=str, required=True, help="Unique scale ID or name")
    parser.add_argument("--baudrate", type=int, default=4800, help="Serial baud rate")
    parser.add_argument("--timeout", type=float, default=1.0, help="Serial read timeout")

    args = parser.parse_args()
    scale_id = args.scale_id

    try:
        scale = SerialScale(
            port=args.device,
            baudrate=args.baudrate,
            timeout=args.timeout,
        )
    except Exception as e:
        print(f"Failed to initialize scale: {e}")
        return

    print(f"Starting FastAPI server for scale '{scale_id}' on port {args.port}")
    uvicorn.run("main:app", host="0.0.0.0", port=args.port, reload=False)


if __name__ == "__main__":
    entrypoint()
