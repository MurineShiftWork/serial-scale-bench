import logging
import re
import statistics
import time
from collections.abc import Callable
from datetime import datetime
from enum import Enum

import serial
from serial import SerialException


class ScaleProtocols(Enum):
    """Known serial protocol variants supported by this driver."""

    Protocol1 = {"id": 1, "format": ""}


class SerialScale:
    """Low-level RS-232/USB serial scale driver.

    Handles raw command/response exchange and protocol detection.
    Prefer the higher-level Scale class for typical use.
    """

    def __init__(
        self,
        port: str,
        baudrate: int = 9600,
        timeout: float = 1,
        protocol: int | None = None,
    ):
        """Open the serial port and detect the scale protocol.

        Args:
            port: Serial device path, e.g. ``/dev/ttyUSB0`` or ``COM3``.
            baudrate: Baud rate matching the scale's RS-232 setting.
            timeout: Per-readline timeout in seconds.
            protocol: Force protocol 1 (multi-line) or 2 (single-line).
                Omit to auto-detect on first connection.
        """
        self.ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=timeout,
        )
        self.protocol: int | None = protocol
        self.last_response_time: datetime | None = None

        self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()

        self._infer_protocol()

    def _send_command(self, command: str):
        """Write an ASCII command terminated with CR LF."""
        if not self.ser.is_open:
            raise serial.SerialException("Serial port is not open.")

        if self.ser.in_waiting:
            self.ser.reset_input_buffer()

        full_command = f"{command}\r\n".encode("ascii")
        self.ser.write(full_command)
        logging.debug(f"Sending command: {command}")

    def _read_lines(self) -> list[str]:
        """Read the expected number of response lines for the active protocol."""
        lines = []

        if self.protocol == 1:
            max_lines = 5
        elif self.protocol == 2:
            max_lines = 1
        else:
            raise NotImplementedError(f"Protocol {self.protocol} is not supported.")

        for _ in range(max_lines):
            line = self.ser.readline().decode("ascii", errors="ignore").strip()
            if line:
                lines.append(line)
        return lines

    def _infer_protocol(self):
        """Auto-detect protocol by sending a print command and inspecting the response."""
        if self.protocol:
            return

        self._send_command("P")
        # Read raw lines without protocol branching (can't use _read_lines here).
        lines = []
        for _ in range(5):
            line = self.ser.readline().decode("ascii", errors="ignore").strip()
            if line:
                lines.append(line)

        if not lines:
            raise RuntimeError("No response from scale during protocol detection.")

        joined = " ".join(lines)
        if any(h in joined for h in ["GS", "No.", "Total"]):
            self.protocol = 1
            logging.info("Bench scale: detected protocol 1 (multi-line GS/NT/GT format)")
        elif re.search(r"[-+]?\s*[\d.]+\s*[a-zA-Z]+", lines[0]):
            self.protocol = 2
            logging.info("Bench scale: detected protocol 2 (single-line format)")

        if self.protocol is None:
            raise RuntimeError(
                f"Could not detect scale protocol from output: {lines}. "
                "Pass protocol=1 or protocol=2 explicitly."
            )

    def get_weight(self) -> float | None:
        """Request the current weight and return it in the scale's native unit.

        Returns None if the scale does not return a parseable value.
        """
        self._send_command("P")
        lines = self._read_lines()

        if not lines:
            return None

        if self.protocol == 1:
            for line in lines:
                if line.startswith(("GS", "NT", "GT")):
                    return self._parse_weight_line(line)
        elif self.protocol == 2:
            return self._parse_weight_line(lines[0])

        return None

    def tare(self):
        """Send the tare command, zeroing the display with the current load."""
        self._send_command("T")

    def zero(self):
        """Send the zero command, resetting the scale's internal zero point."""
        self._send_command("Z")

    def set_tare_value(self, value: float):
        """Preset a known tare value without placing a load on the pan.

        Args:
            value: Tare weight in the scale's native unit.
        """
        self._send_command(f"T{value:.3f}")

    def _parse_weight_line(self, line: str) -> float | None:
        """Extract a floating-point weight from a raw scale response line."""
        line = re.sub(r"^(GS|NT|GT|ST|US)?\s*", "", line)
        match = re.search(r"[-+]?\d+\.\d+", line)
        if match:
            return float(match.group(0))
        return None

    def is_connected(self) -> bool:
        """Return True if the serial port is open."""
        return self.ser and self.ser.is_open

    def is_responsive(self) -> bool:
        """Return True if the scale replies to a print command within the timeout."""
        try:
            self.ser.write(b"P\r\n")
            line = self.ser.readline()
            if line:
                self.last_response_time = datetime.utcnow()
                return True
        except serial.SerialException:
            pass
        return False

    def close(self):
        """Close the serial port."""
        if self.ser.is_open:
            self.ser.close()


class AutoReconnectSerialScale:
    """Wrapper around SerialScale that silently reconnects on serial errors.

    All method calls are forwarded to the underlying SerialScale. If the
    connection is lost, the wrapper reconnects before retrying the call.

    Args:
        *args: Positional arguments forwarded to SerialScale.
        retry_delay: Seconds to wait between reconnection attempts.
        **kwargs: Keyword arguments forwarded to SerialScale.
    """

    def __init__(self, *args, retry_delay=2.0, **kwargs):
        self._args = args
        self._kwargs = kwargs
        self._retry_delay = retry_delay
        self._scale: SerialScale | None = None
        self._connect()

    def _connect(self):
        """Block until a SerialScale connection is established."""
        while True:
            try:
                self._scale = SerialScale(*self._args, **self._kwargs)
                print("SerialScale connected.")
                return
            except SerialException as e:
                print(f"Serial connection failed: {e}. Retrying...")
                time.sleep(self._retry_delay)

    def _ensure_connection(self):
        """Re-connect if the underlying scale is no longer connected."""
        if self._scale is None or not self._scale.is_connected():
            print("Lost connection. Attempting reconnect...")
            self._connect()

    def __getattr__(self, name):
        """Forward method calls to internal SerialScale, with reconnection if needed."""

        def method(*args, **kwargs):
            self._ensure_connection()
            try:
                return getattr(self._scale, name)(*args, **kwargs)
            except SerialException:
                print("Serial error during operation. Reconnecting...")
                self._connect()
                return getattr(self._scale, name)(*args, **kwargs)

        return method


class Scale:
    """High-level bench-scale driver with the same interface as serial-scale-hx711.

    Construction is lightweight; call start() to open the port and infer protocol.
    This allows the same WeighingScaleBase adapter pattern used for the HX711 scale.
    """

    def __init__(
        self,
        serial_port: str,
        baudrate: int = 4800,
        timeout: float = 1.0,
        protocol: int | None = None,
    ) -> None:
        """Store connection parameters without opening the port.

        Args:
            serial_port: Serial device path, e.g. ``/dev/ttyUSB0`` or ``COM3``.
            baudrate: Baud rate matching the scale's RS-232 setting.
            timeout: Per-readline timeout in seconds passed to SerialScale.
            protocol: Force protocol 1 or 2. Omit to auto-detect on start().
        """
        self.serial_port = serial_port
        self.baudrate = baudrate
        self.timeout = timeout
        self.protocol = protocol
        self._scale: SerialScale | None = None

    def start(self, timeout: float = 10.0) -> None:
        """Open the serial port, infer protocol, and verify the scale is responsive.

        Args:
            timeout: Maximum seconds to wait for the scale to respond.

        Raises:
            TimeoutError: If the scale does not respond within ``timeout`` seconds.
        """
        deadline = time.time() + timeout
        last_exc: Exception | None = None
        while time.time() < deadline:
            try:
                if self._scale is not None:
                    self._scale.close()
                    self._scale = None
                self._scale = SerialScale(
                    port=self.serial_port,
                    baudrate=self.baudrate,
                    timeout=self.timeout,
                    protocol=self.protocol,
                )
                if self._scale.is_responsive():
                    logging.info(f"Bench scale ready on {self.serial_port}")
                    return
            except (SerialException, Exception) as exc:
                last_exc = exc
            time.sleep(0.2)
        raise TimeoutError(
            f"Bench scale on {self.serial_port} did not respond within {timeout}s. "
            f"Last error: {last_exc}"
        )

    def tare(self) -> None:
        """Tare the scale and wait briefly for the display to settle."""
        assert self._scale is not None
        self._scale.tare()
        time.sleep(0.3)

    def read_weight(self) -> float | None:
        """Return the current weight, or None if the scale returns no value."""
        assert self._scale is not None
        return self._scale.get_weight()

    def read_weight_repeated(
        self,
        n_readings: int = 5,
        inter_read_delay: float = 0.1,
    ) -> list[float]:
        """Collect multiple weight readings and return all valid ones.

        Args:
            n_readings: Total number of read attempts.
            inter_read_delay: Seconds to wait between attempts.

        Returns:
            List of valid (non-None) weight readings; may be shorter than n_readings.
        """
        readings = []
        for _ in range(n_readings):
            r = self.read_weight()
            if r is not None:
                readings.append(r)
            time.sleep(inter_read_delay)
        return readings

    def read_weight_reliable(
        self,
        n_readings: int = 5,
        inter_read_delay: float = 0.1,
        measure: Callable = statistics.median,
    ) -> float:
        """Return a single reliable weight by aggregating repeated readings.

        Args:
            n_readings: Number of read attempts.
            inter_read_delay: Seconds between attempts.
            measure: Aggregation function applied to valid readings (default: median).

        Returns:
            Aggregated weight value.

        Raises:
            RuntimeError: If no valid readings are obtained.
        """
        readings = self.read_weight_repeated(n_readings, inter_read_delay)
        if not readings:
            raise RuntimeError(
                f"Bench scale on {self.serial_port} returned no valid readings "
                f"after {n_readings} attempts."
            )
        return measure(readings)

    def read_weight_blocking(
        self,
        n_valid: int = 3,
        inter_read_delay: float = 0.2,
        timeout: float = 30.0,
    ) -> float:
        """Block until at least n_valid readings are collected, then return the median.

        Args:
            n_valid: Minimum number of valid readings required.
            inter_read_delay: Seconds between polling attempts.
            timeout: Maximum seconds to wait before raising TimeoutError.

        Returns:
            Median of the collected readings.

        Raises:
            TimeoutError: If n_valid readings cannot be collected within timeout.
        """
        readings = []
        deadline = time.time() + timeout
        while time.time() < deadline:
            r = self.read_weight()
            if r is not None:
                readings.append(r)
                if len(readings) >= n_valid:
                    return statistics.median(readings)
            time.sleep(inter_read_delay)
        raise TimeoutError(
            f"Bench scale on {self.serial_port} could not produce {n_valid} valid "
            f"readings within {timeout}s."
        )

    def disconnect(self) -> None:
        """Close the serial port and release the underlying SerialScale."""
        if self._scale is not None:
            self._scale.close()
            self._scale = None

    def __del__(self) -> None:
        self.disconnect()


if __name__ == "__main__":
    scale = SerialScale("/dev/ttyUSB0", protocol=2)

    if scale.is_connected():
        print("Scale is connected.")
        if scale.is_responsive():
            print("Scale is responsive.")
            print("Current weight:", scale.get_weight())
        else:
            print("Scale is unresponsive.")
    else:
        print("Scale not connected.")

    scale.close()
