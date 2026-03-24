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

    config = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    output_dir = Path(args.output_dir)

    model = config.get("model", {})
    training = config.get("training", {})
    loss = config.get("loss", {})

    width = float(model.get("width", 32))
    depth = float(model.get("depth", 2))
    lr = float(training.get("lr", 1e-3))
    sw = float(loss.get("smoothness_weight", 0.0))

    rel_l2 = 0.095 - 0.00035 * width - 0.003 * depth + 6.0 * abs(lr - 5e-4) - 0.18 * sw
    shock_error = 0.045 - 0.25 * sw + 0.00008 * width + 0.001 * max(depth - 2, 0)
    runtime_seconds = 1.3 + 0.012 * width + 0.18 * depth

    payload = {
        "rel_l2": round(max(rel_l2, 0.008), 6),
        "shock_error": round(max(shock_error, 0.002), 6),
        "runtime_seconds": round(runtime_seconds, 4),
        "status": "trained",
    }

    (output_dir / "train_artifact.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
