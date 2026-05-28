import logging
import re
from datetime import datetime
from enum import Enum

import serial


class ScaleProtocols(Enum):
    Protocol1 = {"id": 1, "format": ""}


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

        match = re.search(r"[-+]? *([\d.]+)\s*([a-zA-Z]+)", lines[0])
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
