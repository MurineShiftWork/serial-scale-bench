# serial-scale-bench

Python driver for RS-232/USB commercial bench scales (Kern, Mettler-Toledo, etc.).

Supports two ASCII response protocols:
- **Protocol 1** — multi-line header responses (`GS`, `NT`, `GT` prefixes); typical of
  Kern and similar label-printing scales
- **Protocol 2** — single float line; minimal scales and simpler firmware

Protocol is auto-detected on first connection. A FastAPI HTTP server is included for
running the scale as a networked service (e.g. LabWatch integration).

## Install

Base (serial only):

```bash
pip install serial-scale-bench
```

With HTTP API server:

```bash
pip install "serial-scale-bench[api]"
```

Or editable from this repo:

```bash
pip install -e .
```

## Usage

```python
from serial_scale_bench import SerialScale

scale = SerialScale(port="/dev/ttyUSB0", baudrate=9600)
scale.tare()
weight = scale.get_weight()   # float grams or None
scale.close()
```

### Auto-reconnect wrapper

```python
from serial_scale_bench import AutoReconnectSerialScale

scale = AutoReconnectSerialScale(port="/dev/ttyUSB0")
weight = scale.get_weight()   # reconnects automatically on error
```

## HTTP API server

Start a local REST server exposing the scale over HTTP:

```bash
python -m serial_scale_bench.entrypoint --device /dev/ttyUSB0 --port 8080 --scale-id bench1
```

Endpoints: `GET /weight`, `POST /tare`, `POST /zero`, `GET /status`, `GET /ping`.

## API reference

| Method | Description |
|---|---|
| `get_weight()` | Poll current weight (float or None) |
| `tare()` | Send tare command |
| `zero()` | Send zero command |
| `set_tare_value(value)` | Set absolute tare |
| `is_connected()` | True if serial port is open |
| `is_responsive()` | True if scale responds to ping |
| `close()` | Close serial connection |

## murineshiftwork integration

Planned: `BenchScaleAdapter` in `murineshiftwork.logic.scale`. Install with:

```bash
pip install "murineshiftwork[calibration]"
```
