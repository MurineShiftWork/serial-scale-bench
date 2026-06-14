# Protocols

## Serial protocol overview

The driver communicates with bench scales over RS-232 or USB-serial using ASCII
commands and responses. All commands are terminated with CR LF (`\r\n`). The
scale replies with one or more ASCII lines, also CR LF terminated.

The following commands are used:

| Command | Effect |
|---------|--------|
| `P` | Print/poll current weight |
| `T` | Tare (zero display with load on pan) |
| `T<value>` | Preset absolute tare value |
| `Z` | Zero (reset internal zero reference) |

## Protocol variants

Two response formats are supported:

**Protocol 1 - multi-line (Kern and similar):** The scale returns up to five
lines. Weight lines are prefixed with `GS` (gross), `NT` (net), or `GT`
(grand total). The driver reads up to five lines and selects the first line
matching one of those prefixes.

**Protocol 2 - single-line (minimal firmware):** The scale returns one line
containing a numeric value followed by a unit, e.g. `123.45 g`. The driver
reads that single line and extracts the float.

## Protocol auto-detection

On the first connection the driver sends a `P` command and reads up to five raw
lines. Detection logic (in `SerialScale._infer_protocol`):

1. If any line contains `GS`, `No.`, or `Total` - Protocol 1 is selected.
2. Otherwise, if the first line matches the pattern `[-+]?\s*[\d.]+\s*[a-zA-Z]+`
   (a number followed by a unit) - Protocol 2 is selected.
3. If neither condition matches, a `RuntimeError` is raised and the caller must
   pass `protocol=1` or `protocol=2` explicitly to bypass detection.

## Calibration workflow

The `Scale` class supports a simple tare-based calibration:

1. Remove all load from the pan.
2. Call `scale.tare()` to zero the display.
3. Place a known reference weight and call `scale.read_weight_reliable()` to
   record the reading.
4. If the reading does not match the reference, adjust the scale's physical
   calibration trimmer and repeat.

For scripted calibration, `set_tare_value(value)` presets a known tare without
requiring a load, which is useful when the tare container weight is known in
advance.

## MSW integration

`serial-scale-bench` is designed as a hardware driver layer. A planned
`BenchScaleAdapter` in `murineshiftwork.logic.scale` will wrap the `Scale`
class behind the shared `WeighingScaleBase` interface used across the
murineshiftwork stack, allowing the bench scale to be used interchangeably
with the HX711-based scale in experiment logic. Install the integration with:

```bash
pip install "murineshiftwork[calibration]"
```
