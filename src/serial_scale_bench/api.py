import socket
from datetime import datetime

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from serial_scale_bench.scale import AutoReconnectSerialScale


class ScaleStatus(BaseModel):
    scale_id: str
    is_connected: bool
    last_seen: datetime | None = None
    protocol: str | None = None


def create_api(scale: AutoReconnectSerialScale, instance_info: dict) -> FastAPI:
    """"""
    app = FastAPI()
    app.state.scale = scale
    app.state.instance_info = (
        instance_info  # TODO: instance id/name, api host/port, serial port/baud rate
    )

    @app.get("/status", response_model=ScaleStatus)
    def get_scale_info():
        return ScaleStatus(
            scale_id=app.state.instance_info["scale_id"],
            is_connected=app.state.scale.is_connected(),
            last_seen=app.state.scale.last_response_time,
            protocol=app.state.scale.protocol,
        )

    @app.get("/ping")
    def ping_scale():
        return {"responsive": app.state.scale.is_responsive()}

    @app.get("/info")
    def get_info():
        return {
            "scale_id": app.state.instance_info,
            "hostname": socket.gethostname(),
            "port": app.state.instance_info["port"],
        }

    @app.get("/weight")
    def read_weight():
        if not app.state.scale.is_responsive():
            raise HTTPException(status_code=503, detail="Scale not responsive")
        weight = app.state.scale.get_weight()
        if weight is None:
            raise HTTPException(status_code=204, detail="No weight read")
        return {"scale_id": instance_info["id"], "weight": weight}

    @app.post("/tare")
    def tare_scale():
        if not app.state.scale.is_responsive():
            raise HTTPException(status_code=503, detail="Scale not responsive")
        app.state.scale.tare()
        return {"scale_id": instance_info["id"], "action": "tared"}

    @app.post("/zero")
    def zero_scale():
        if not app.state.scale.is_responsive():
            raise HTTPException(status_code=503, detail="Scale not responsive")
        app.state.scale.zero()
        return {"scale_id": instance_info["id"], "action": "zeroed"}

    return app
