import uvicorn

from serial_scale.cli import cli_parser


def entrypoint():

    args = cli_parser()

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
