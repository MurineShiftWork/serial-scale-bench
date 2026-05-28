import sys


def test_python_version() -> None:
    assert sys.version_info >= (3, 10)


def test_package_importable() -> None:
    import serial_scale_bench

    assert hasattr(serial_scale_bench, "__version__")
