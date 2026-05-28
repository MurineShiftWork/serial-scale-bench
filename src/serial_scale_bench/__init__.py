__author__ = "Lars B. Rollik"

from importlib.metadata import PackageNotFoundError, version

from serial_scale_bench.scale import AutoReconnectSerialScale, Scale, SerialScale

try:
    __version__ = version("serial-scale-bench")
except PackageNotFoundError:
    __version__ = "unknown"

__all__ = ["Scale", "SerialScale", "AutoReconnectSerialScale", "__version__"]
