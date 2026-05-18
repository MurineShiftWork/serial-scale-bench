# scale.py
import time

from original_serial_scale import SerialScale  # your base class from earlier
from serial import SerialException


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
