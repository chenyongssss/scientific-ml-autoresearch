from pathlib import Path

from autoresearch.storage import dump_yaml, load_yaml


def test_yaml_roundtrip(tmp_path: Path):
    path = tmp_path / "a.yaml"
    payload = {"x": 1, "y": {"z": 2}}
    dump_yaml(path, payload)
    assert load_yaml(path) == payload
