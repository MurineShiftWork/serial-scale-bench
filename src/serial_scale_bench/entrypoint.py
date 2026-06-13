import uvicorn

from serial_scale_bench.cli import cli_parser
from serial_scale_bench.scale import AutoReconnectSerialScale


def entrypoint():
    """Entry point for the ``serial-scale-bench`` CLI command.

    Reads CLI arguments, opens the serial scale, and starts the uvicorn server.
    """
    args = cli_parser()

    scale_id = args.scale_id

    _scale = AutoReconnectSerialScale(
        port=args.device,
        baudrate=args.baudrate,
        timeout=args.timeout,
    )

    print(f"Running FastAPI server for scale '{scale_id}' on port {args.port}")
    uvicorn.run("serial_scale_bench.api:app", host="0.0.0.0", port=args.port, reload=False)


if __name__ == "__main__":
    entrypoint()
