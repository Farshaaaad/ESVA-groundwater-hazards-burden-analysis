# -*- coding: utf-8 -*-
"""
Run the tabular portion of the ESVA reproducibility workflow.

Run 01_calculate_swi.py in ArcGIS Pro first, export the corrected feature
class to CSV or Excel, and then use this script to recalculate risk/burden
metrics, generate service-status tables, calculate representation ratios,
and optionally create SWI composite figures.

Author: Farshad Hesamfar
Affiliation: University of Virginia
Contact: wky7xx@virginia.edu
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def run(command: list[str]) -> None:
    print("\nRunning:", " ".join(command))
    subprocess.run(command, check=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--sheet", default=None)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument(
        "--make-figures",
        action="store_true",
        help="Create SWI composite exposure figures.",
    )
    args = parser.parse_args()

    code_dir = Path(__file__).resolve().parent
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    metrics_output = output_dir / "metrics_recalculated.csv"

    command = [
        sys.executable,
        str(code_dir / "02_calculate_risk_and_burden.py"),
        "--input",
        args.input,
        "--output",
        str(metrics_output),
        "--qa-output",
        str(output_dir / "risk_burden_qa.csv"),
    ]
    if args.sheet:
        command += ["--sheet", args.sheet]
    run(command)

    run(
        [
            sys.executable,
            str(code_dir / "03_generate_service_status_tables.py"),
            "--input",
            str(metrics_output),
            "--output-dir",
            str(output_dir / "tables"),
        ]
    )

    run(
        [
            sys.executable,
            str(code_dir / "04_calculate_representation_ratios.py"),
            "--input",
            str(metrics_output),
            "--output",
            str(output_dir / "representation_ratios.csv"),
        ]
    )

    if args.make_figures:
        run(
            [
                sys.executable,
                str(code_dir / "05_create_swi_exposure_figures.py"),
                "--input",
                str(metrics_output),
                "--output-dir",
                str(output_dir / "figures"),
            ]
        )

    print("\nTabular workflow completed successfully.")
    print(f"Outputs are in: {output_dir}")


if __name__ == "__main__":
    main()
