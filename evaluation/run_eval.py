#!/usr/bin/env python3
"""
Run golden questions against the pipeline and emit scores (week 3).

Usage (future): python -m evaluation.run_eval --output reports/eval.json
"""

from __future__ import annotations

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="Lumen evaluation runner")
    parser.add_argument(
        "--golden",
        default="evaluation/golden_questions.yaml",
        help="Path to golden YAML",
    )
    _ = parser.parse_args()
    raise NotImplementedError("Week 3: load golden set, invoke pipeline, score metrics.")


if __name__ == "__main__":
    main()
