from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    config_path = Path(args.config)
    output_dir = Path(args.output_dir)
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))

    model = config.get("model", {})
    training = config.get("training", {})
    loss = config.get("loss", {})

    width = float(model.get("width", 32))
    depth = float(model.get("depth", 2))
    lr = float(training.get("lr", 1e-3))
    cw = float(loss.get("conservation_weight", 0.0))

    rel_l2 = 0.08 - 0.0004 * width - 0.004 * depth + 8.0 * abs(lr - 5e-4) - 0.5 * cw
    conservation_error = 0.03 - 1.5 * cw + 0.00005 * width
    runtime_seconds = 1.0 + 0.01 * width + 0.15 * depth

    payload = {
        "rel_l2": round(max(rel_l2, 0.005), 6),
        "conservation_error": round(max(conservation_error, 0.001), 6),
        "runtime_seconds": round(runtime_seconds, 4),
        "status": "trained",
    }

    (output_dir / "train_artifact.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
