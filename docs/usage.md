# Usage

## Single reading

The simplest case: open the scale, read once, close.

```python
from serial_scale_bench import Scale

scale = Scale("/dev/ttyUSB0", baudrate=4800)
scale.start()
print(scale.read_weight())
scale.disconnect()
```

`read_weight()` returns `None` when the scale returns no parseable value
(display blank, motion, or communication glitch). Always check for `None`
before using the result.

## Reliable reading with aggregation

`read_weight_reliable()` collects several readings and reduces them to a single
value with an aggregation function (default: median). Use this when a single
reading is not trustworthy.

```python
weight = scale.read_weight_reliable(n_readings=5, inter_read_delay=0.1)
print(f"Median weight: {weight}")
```

Pass any callable that accepts a list of floats as the `measure` argument:

```python
import statistics
weight = scale.read_weight_reliable(measure=statistics.mean)
```

## Blocking until stable

`read_weight_blocking()` polls until it collects a minimum number of valid
readings, then returns their median. Useful when you need to wait for a load
to settle.

```python
weight = scale.read_weight_blocking(n_valid=3, inter_read_delay=0.2, timeout=30.0)
```

Raises `TimeoutError` if the required readings cannot be collected within the
timeout.

## Continuous reading

Poll in a loop for continuous logging:

```python
import time
from serial_scale_bench import Scale

scale = Scale("/dev/ttyUSB0", baudrate=4800)
scale.start()

try:
    while True:
        w = scale.read_weight()
        if w is not None:
            print(f"{w:.3f}")
        time.sleep(0.5)
except KeyboardInterrupt:
    pass
finally:
    scale.disconnect()
```

## Taring

Send the tare command to zero the display with the current load on the pan:

```python
scale.tare()   # waits 0.3 s for the display to settle
```

## Auto-reconnect wrapper

`AutoReconnectSerialScale` silently reconnects on serial errors. It is used
internally by the HTTP server but can also be used in scripts that must survive
cable disconnections.

```python
from serial_scale_bench import AutoReconnectSerialScale

scale = AutoReconnectSerialScale("/dev/ttyUSB0", baudrate=4800, retry_delay=2.0)
print(scale.get_weight())
scale.close()
```

## Error handling

| Situation | Exception |
|-----------|-----------|
| Port not found or inaccessible | `serial.SerialException` from `start()` |
| Scale not responding within start timeout | `TimeoutError` from `Scale.start()` |
| No valid readings collected | `RuntimeError` from `read_weight_reliable()` |
| Blocking read timed out | `TimeoutError` from `read_weight_blocking()` |

```python
from serial import SerialException
from serial_scale_bench import Scale

try:
    scale = Scale("/dev/ttyUSB0")
    scale.start(timeout=5.0)
    weight = scale.read_weight_reliable()
except SerialException as exc:
    print(f"Serial port error: {exc}")
except TimeoutError as exc:
    print(f"Scale did not respond: {exc}")
finally:
    scale.disconnect()
```

## HTTP server

The package ships a built-in FastAPI server that exposes the scale over HTTP.
Run it from the command line:

```bash
serial-scale-bench --device /dev/ttyUSB0 --baudrate 4800 --scale-id bench-1 --port 8000
```

Endpoints:

| Method | Path | Description |
|--------|------|-------------|
| GET | `/weight` | Current weight reading |
| GET | `/status` | Connection and protocol info |
| GET | `/ping` | Liveness check |
| GET | `/info` | Instance metadata |
| POST | `/tare` | Tare the scale |
| POST | `/zero` | Zero the scale |
