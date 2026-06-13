# Getting Started

## Installation

```bash
pip install serial-scale-bench
```

The package requires Python 3.10 or newer. The only non-stdlib dependency is
[pyserial](https://pypi.org/project/pyserial/), which is installed automatically.

## Connecting to the scale

Bench scales with an RS-232 or USB-serial interface appear as a serial device
on the host operating system:

- Linux/macOS: `/dev/ttyUSB0`, `/dev/ttyACM0`, `/dev/cu.usbserial-*`
- Windows: `COM3`, `COM4`, etc.

The baud rate must match the setting on the scale itself (common values: 4800,
9600). Consult your scale's manual if unsure.

## Reading a weight

The `Scale` class is the recommended entry point. Construction is cheap; the
port is only opened when you call `start()`.

```python
from serial_scale_bench import Scale

scale = Scale(serial_port="/dev/ttyUSB0", baudrate=4800)
scale.start()           # opens the port and detects protocol

weight = scale.read_weight()   # returns float (grams/kg, native unit) or None
print(weight)

scale.disconnect()
```

Use as a context is not built in, so remember to call `disconnect()` when done,
or rely on the finaliser in long-running scripts.

## Forcing a protocol

The driver auto-detects the serial protocol (multi-line vs single-line response
format) on first connection. If detection fails, pass the protocol number
explicitly:

```python
scale = Scale("/dev/ttyUSB0", baudrate=9600, protocol=2)
scale.start()
```

Protocol 1 covers scales that return multi-line GS/NT/GT headers (e.g. Kern
series). Protocol 2 covers scales that return a single line with a value and
unit.
