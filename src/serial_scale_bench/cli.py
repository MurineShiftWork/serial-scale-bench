import argparse
import os


def cli_parser():
    """Parse command-line arguments for the serial-scale-bench HTTP server."""
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
    return args
