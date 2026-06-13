import socket
from datetime import datetime

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from serial_scale_bench.scale import AutoReconnectSerialScale


class ScaleStatus(BaseModel):
    """Connection and protocol status for a single scale instance."""

    scale_id: str
    is_connected: bool
    last_seen: datetime | None = None
    protocol: str | None = None


def create_api(scale: AutoReconnectSerialScale, instance_info: dict) -> FastAPI:
    """Build and return a FastAPI application that exposes a scale over HTTP.

    Args:
        scale: Auto-reconnecting scale instance to serve.
        instance_info: Mapping with at least ``scale_id`` and ``port`` keys.

    Returns:
        Configured FastAPI application (not yet running).
    """
    app = FastAPI()
    app.state.scale = scale
    app.state.instance_info = (
        instance_info  # TODO: instance id/name, api host/port, serial port/baud rate
    )

    @app.get("/status", response_model=ScaleStatus)
    def get_scale_info():
        """Return connection status and detected protocol for this scale."""
        return ScaleStatus(
            scale_id=app.state.instance_info["scale_id"],
            is_connected=app.state.scale.is_connected(),
            last_seen=app.state.scale.last_response_time,
            protocol=app.state.scale.protocol,
        )

    @app.get("/ping")
    def ping_scale():
        """Return whether the scale replies to a print command right now."""
        return {"responsive": app.state.scale.is_responsive()}

    @app.get("/info")
    def get_info():
        """Return instance metadata including hostname and HTTP port."""
        return {
            "scale_id": app.state.instance_info,
            "hostname": socket.gethostname(),
            "port": app.state.instance_info["port"],
        }

    @app.get("/weight")
    def read_weight():
        """Return the current weight reading from the scale.

        Raises 503 if the scale is unresponsive, or 204 if no value can be parsed.
        """
        if not app.state.scale.is_responsive():
            raise HTTPException(status_code=503, detail="Scale not responsive")
        weight = app.state.scale.get_weight()
        if weight is None:
            raise HTTPException(status_code=204, detail="No weight read")
        return {"scale_id": instance_info["id"], "weight": weight}

    @app.post("/tare")
    def tare_scale():
        """Send the tare command to zero the display with the current load."""
        if not app.state.scale.is_responsive():
            raise HTTPException(status_code=503, detail="Scale not responsive")
        app.state.scale.tare()
        return {"scale_id": instance_info["id"], "action": "tared"}

    @app.post("/zero")
    def zero_scale():
        """Send the zero command to reset the scale's internal zero point."""
        if not app.state.scale.is_responsive():
            raise HTTPException(status_code=503, detail="Scale not responsive")
        app.state.scale.zero()
        return {"scale_id": instance_info["id"], "action": "zeroed"}

    return app
