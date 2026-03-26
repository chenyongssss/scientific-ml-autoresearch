from autoresearch.evidence import aggregate_branch_evidence, claim_taxonomy_from_cards
from autoresearch.schemas import ExperimentResult, ScientificCheckResult, TaskSpec


def test_aggregate_branch_evidence_groups_seeds_and_regimes():
    task = TaskSpec(
        name="demo",
        workspace=".",
        commands={"train": "x", "eval": "y"},
        metrics={"primary": ["rel_l2"]},
        planner={"baseline": {"model.width": 32}},
        reporting={"sort_by": "rel_l2", "lower_is_better": True},
    )
    results = [
        ExperimentResult(
            experiment_id="exp_001",
            round_index=1,
            status="ok",
            metrics={"rel_l2": 0.10},
            config={"model.width": 64, "seed": 0, "evaluation_regime": "default"},
            run_dir="a",
            scientific_checks=[ScientificCheckResult(name="conservation", kind="constraint", status="passed")],
        ),
        ExperimentResult(
            experiment_id="exp_002",
            round_index=1,
            status="ok",
            metrics={"rel_l2": 0.12},
            config={"model.width": 64, "seed": 1, "evaluation_regime": "harder"},
            run_dir="b",
            scientific_checks=[ScientificCheckResult(name="shifted-grid", kind="robustness", status="pending")],
        ),
        ExperimentResult(
            experiment_id="exp_003",
            round_index=1,
            status="ok",
            metrics={"rel_l2": 0.20},
            config={"model.width": 32, "seed": 0, "evaluation_regime": "default"},
            run_dir="c",
        ),
    ]
    cards = aggregate_branch_evidence(task, results)
    assert len(cards) == 2
    best = cards[0]
    assert best["branch_label"] == "model.width"
    assert best["count"] == 2
    assert best["seed_count"] == 2
    assert best["regime_count"] == 2
    assert best["evidence_status"] == "promising"


def test_claim_taxonomy_uses_best_card():
    cards = [
        {"branch_label": "a", "evidence_status": "validated", "mean": 0.1},
        {"branch_label": "b", "evidence_status": "observed", "mean": 0.2},
    ]
    assert claim_taxonomy_from_cards(cards) == "validated"
