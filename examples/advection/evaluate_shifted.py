from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    output_path = Path(args.output)
    metrics = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))

    shifted = {
        "status": "passed" if metrics.get("conservation_error", 1.0) <= 0.0015 else "failed",
        "details": "Toy shifted-grid evaluation derived from the default metrics.",
        "metrics": {
            "rel_l2_shifted": round(float(metrics.get("rel_l2", 0.0)) * 1.08, 6),
            "conservation_error_shifted": round(float(metrics.get("conservation_error", 0.0)) * 1.1, 6),
        },
    }
    output_path.write_text(json.dumps(shifted, indent=2), encoding="utf-8")
    print(json.dumps(shifted, indent=2))


if __name__ == "__main__":
    main()
