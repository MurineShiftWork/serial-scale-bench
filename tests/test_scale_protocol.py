"""Tests for SerialScale protocol detection and Scale high-level driver.

All serial I/O is mocked — no physical hardware required.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from serial_scale_bench.scale import Scale, SerialScale

# ---------------------------------------------------------------------------
# Helpers


def _make_serial_scale(responses: list[bytes], protocol: int | None = None) -> SerialScale:
    """Build a SerialScale with a mocked serial port returning *responses* on readline()."""
    with patch("serial_scale_bench.scale.serial.Serial") as mock_serial_cls:
        mock_ser = MagicMock()
        mock_ser.is_open = True
        mock_ser.in_waiting = 0
        mock_ser.readline.side_effect = responses
        mock_serial_cls.return_value = mock_ser
        scale = SerialScale(port="/dev/ttyUSB0", protocol=protocol)
    scale.ser = mock_ser
    return scale


# ---------------------------------------------------------------------------
# _infer_protocol — protocol 1 detection


def test_infer_protocol_detects_protocol1_from_gs_prefix():
    with patch("serial_scale_bench.scale.serial.Serial") as mock_cls:
        mock_ser = MagicMock()
        mock_ser.is_open = True
        mock_ser.in_waiting = 0
        mock_ser.readline.side_effect = [
            b"No. 001\r\n",
            b"GS  0.123 kg\r\n",
            b"Total  0.123 kg\r\n",
            b"",
            b"",
        ]
        mock_cls.return_value = mock_ser
        scale = SerialScale(port="/dev/ttyUSB0", protocol=None)
    assert scale.protocol == 1


def test_infer_protocol_detects_protocol1_from_total_prefix():
    with patch("serial_scale_bench.scale.serial.Serial") as mock_cls:
        mock_ser = MagicMock()
        mock_ser.is_open = True
        mock_ser.in_waiting = 0
        mock_ser.readline.side_effect = [b"Total  1.500 g\r\n", b"", b"", b"", b""]
        mock_cls.return_value = mock_ser
        scale = SerialScale(port="/dev/ttyUSB0", protocol=None)
    assert scale.protocol == 1


# ---------------------------------------------------------------------------
# _infer_protocol — protocol 2 detection


def test_infer_protocol_detects_protocol2_from_single_line():
    with patch("serial_scale_bench.scale.serial.Serial") as mock_cls:
        mock_ser = MagicMock()
        mock_ser.is_open = True
        mock_ser.in_waiting = 0
        mock_ser.readline.side_effect = [b"+  1.234 g\r\n", b"", b"", b"", b""]
        mock_cls.return_value = mock_ser
        scale = SerialScale(port="/dev/ttyUSB0", protocol=None)
    assert scale.protocol == 2


def test_infer_protocol_detects_protocol2_signed_negative():
    with patch("serial_scale_bench.scale.serial.Serial") as mock_cls:
        mock_ser = MagicMock()
        mock_ser.is_open = True
        mock_ser.in_waiting = 0
        mock_ser.readline.side_effect = [b"-  0.005 kg\r\n", b"", b"", b"", b""]
        mock_cls.return_value = mock_ser
        scale = SerialScale(port="/dev/ttyUSB0", protocol=None)
    assert scale.protocol == 2


# ---------------------------------------------------------------------------
# _infer_protocol — no response raises


def test_infer_protocol_raises_on_empty_response():
    with patch("serial_scale_bench.scale.serial.Serial") as mock_cls:
        mock_ser = MagicMock()
        mock_ser.is_open = True
        mock_ser.in_waiting = 0
        mock_ser.readline.return_value = b""
        mock_cls.return_value = mock_ser
        with pytest.raises(RuntimeError, match="No response from scale"):
            SerialScale(port="/dev/ttyUSB0", protocol=None)


def test_infer_protocol_raises_on_unrecognized_output():
    with patch("serial_scale_bench.scale.serial.Serial") as mock_cls:
        mock_ser = MagicMock()
        mock_ser.is_open = True
        mock_ser.in_waiting = 0
        mock_ser.readline.side_effect = [b"???JUNK???\r\n", b"", b"", b"", b""]
        mock_cls.return_value = mock_ser
        with pytest.raises(RuntimeError, match="Could not detect scale protocol"):
            SerialScale(port="/dev/ttyUSB0", protocol=None)


# ---------------------------------------------------------------------------
# _infer_protocol — explicit protocol skips detection


def test_explicit_protocol_skips_detection():
    with patch("serial_scale_bench.scale.serial.Serial") as mock_cls:
        mock_ser = MagicMock()
        mock_ser.is_open = True
        mock_ser.in_waiting = 0
        mock_cls.return_value = mock_ser
        scale = SerialScale(port="/dev/ttyUSB0", protocol=2)
    # No P command sent during init when protocol is explicit
    assert scale.protocol == 2
    mock_ser.write.assert_not_called()


# ---------------------------------------------------------------------------
# Scale.start() passes protocol=None to SerialScale (allows detection)


def test_scale_start_passes_none_protocol_when_unset():
    scale = Scale(serial_port="/dev/ttyUSB0", protocol=None)
    with patch("serial_scale_bench.scale.SerialScale") as mock_cls:
        mock_instance = MagicMock()
        mock_instance.is_responsive.return_value = True
        mock_cls.return_value = mock_instance
        scale.start()
    _, kwargs = mock_cls.call_args
    assert kwargs["protocol"] is None


def test_scale_start_passes_explicit_protocol_through():
    scale = Scale(serial_port="/dev/ttyUSB0", protocol=1)
    with patch("serial_scale_bench.scale.SerialScale") as mock_cls:
        mock_instance = MagicMock()
        mock_instance.is_responsive.return_value = True
        mock_cls.return_value = mock_instance
        scale.start()
    _, kwargs = mock_cls.call_args
    assert kwargs["protocol"] == 1


# ---------------------------------------------------------------------------
# _parse_weight_line


def test_parse_weight_line_protocol2_plain():
    with patch("serial_scale_bench.scale.serial.Serial") as mock_cls:
        mock_ser = MagicMock()
        mock_ser.is_open = True
        mock_ser.in_waiting = 0
        mock_ser.readline.side_effect = [b"+  1.234 g\r\n", b"", b"", b"", b""]
        mock_cls.return_value = mock_ser
        scale = SerialScale(port="/dev/ttyUSB0", protocol=None)
    assert scale._parse_weight_line("  1.234 g") == pytest.approx(1.234)


def test_parse_weight_line_protocol1_gs_prefix():
    with patch("serial_scale_bench.scale.serial.Serial") as mock_cls:
        mock_ser = MagicMock()
        mock_ser.is_open = True
        mock_ser.in_waiting = 0
        mock_ser.readline.side_effect = [b"GS  0.567 kg\r\n", b"No.\r\n", b"", b"", b""]
        mock_cls.return_value = mock_ser
        scale = SerialScale(port="/dev/ttyUSB0", protocol=None)
    assert scale._parse_weight_line("GS  0.567 kg") == pytest.approx(0.567)


def test_parse_weight_line_returns_none_on_no_number():
    with patch("serial_scale_bench.scale.serial.Serial") as mock_cls:
        mock_ser = MagicMock()
        mock_ser.is_open = True
        mock_ser.in_waiting = 0
        mock_ser.readline.side_effect = [b"+  1.0 g\r\n", b"", b"", b"", b""]
        mock_cls.return_value = mock_ser
        scale = SerialScale(port="/dev/ttyUSB0", protocol=None)
    assert scale._parse_weight_line("no digits here") is None
