import importlib.metadata


def test_version_is_nonempty_str() -> None:
    version = importlib.metadata.version("serial-scale-bench")
    assert isinstance(version, str)
    assert version
