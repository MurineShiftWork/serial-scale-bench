from serial import SerialException

import logging
import re
import statistics
import time
from collections.abc import Callable
from datetime import datetime

import serial
from enum import Enum

class ScaleProtocols(Enum):
    Protocol1 = {
        "id": 1,
        "format": ""
    }

class SerialScale:
    def __init__(
        self,
        port: str,
        baudrate: int = 9600,
        timeout: float = 1,
        protocol: int = 2,
    ):
        self.ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=timeout,
        )
        self.protocol: int | None = protocol
        self.last_response_time = None

        self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()

        self._infer_protocol()

    def _send_command(self, command: str):
        if not self.ser.is_open:
            raise serial.SerialException("Serial port is not open.")

        if self.ser.in_waiting:
            self.ser.reset_input_buffer()

        full_command = f"{command}\n\r".encode("ascii")
        self.ser.write(full_command)
        logging.debug(f"Sending command: {command}")

    def _read_lines(self) -> list[str]:
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
        if self.protocol:
            return

        self._send_command("P")
        lines = self._read_lines()

        if not lines:
            raise RuntimeError("No response from scale.")

        joined = " ".join(lines)
        if any(h in joined for h in ["GS", "No.", "Total"]):
            self.protocol = 1

        match = re.search(r'[-+]? *([\d.]+)\s*([a-zA-Z]+)', lines[0])
        if match:
            self.protocol = 2

        if self.protocol is None:
            raise RuntimeError(f"Unrecognized scale output: {lines}")

    def get_weight(self) -> float | None:
        """"""
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
        self._send_command("T")

    def zero(self):
        self._send_command("Z")

    def set_tare_value(self, value: float):
        self._send_command(f"T{value:.3f}")

    def _parse_weight_line(self, line: str) -> float | None:
        line = re.sub(r"^(GS|NT|GT|ST|US)?\s*", "", line)
        match = re.search(r"[-+]?\d+\.\d+", line)
        if match:
            return float(match.group(0))
        return None

    def is_connected(self) -> bool:
        return self.ser and self.ser.is_open

    def is_responsive(self) -> bool:
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
        if self.ser.is_open:
            self.ser.close()



class AutoReconnectSerialScale:
    def __init__(self, *args, retry_delay=2.0, **kwargs):
        self._args = args
        self._kwargs = kwargs
        self._retry_delay = retry_delay
        self._scale: SerialScale | None = None
        self._connect()

    def _connect(self):
        while True:
            try:
                self._scale = SerialScale(*self._args, **self._kwargs)
                print("SerialScale connected.")
                return
            except SerialException as e:
                print(f"Serial connection failed: {e}. Retrying...")
                time.sleep(self._retry_delay)

    def _ensure_connection(self):
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
        baudrate: int = 9600,
        timeout: float = 1.0,
        protocol: int | None = None,
    ) -> None:
        self.serial_port = serial_port
        self.baudrate = baudrate
        self.timeout = timeout
        self.protocol = protocol
        self._scale: SerialScale | None = None

    def start(self, timeout: float = 10.0) -> None:
        """Open the serial port, infer protocol, and verify the scale is responsive."""
        deadline = time.time() + timeout
        last_exc: Exception | None = None
        while time.time() < deadline:
            try:
                self._scale = SerialScale(
                    port=self.serial_port,
                    baudrate=self.baudrate,
                    timeout=self.timeout,
                    protocol=self.protocol or 2,
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
        self._scale.tare()
        time.sleep(0.3)

    def read_weight(self) -> float | None:
        return self._scale.get_weight()

    def read_weight_repeated(
        self,
        n_readings: int = 5,
        inter_read_delay: float = 0.1,
    ) -> list[float]:
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
