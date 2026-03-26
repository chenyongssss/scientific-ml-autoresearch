from pathlib import Path

from autoresearch.storage import evidence_state_path, load_latest_evidence_state, save_evidence_state


def test_save_evidence_state_writes_json(tmp_path: Path):
    payload = {"claim_taxonomy": "observed", "branch_cards": [{"branch_label": "baseline"}]}
    path = save_evidence_state(tmp_path, 1, payload)
    assert path == evidence_state_path(tmp_path, 1)
    assert path.exists()
    assert 'claim_taxonomy' in path.read_text(encoding='utf-8')


def test_load_latest_evidence_state_returns_latest(tmp_path: Path):
    save_evidence_state(tmp_path, 1, {"claim_taxonomy": "observed"})
    save_evidence_state(tmp_path, 2, {"claim_taxonomy": "validated"})
    latest = load_latest_evidence_state(tmp_path)
    assert latest is not None
    assert latest["claim_taxonomy"] == "validated"
