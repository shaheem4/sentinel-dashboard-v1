"""Synthetic sensor pipeline: FFT -> Isolation Forest -> state -> CSV."""

from __future__ import annotations

import argparse
import csv
import pickle
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from baseline_calibration import MODEL_PATH, SAMPLE_RATE, WINDOW_SIZE, feature_vector, make_window, train_model
from state_machine import StateMachine

CSV_PATH = Path(__file__).resolve().parent / "mock_data" / "sensor_log.csv"
CSV_FIELDS = ["timestamp", "vibration", "acoustic", "pressure", "temperature", "strain", "status"]


def load_model():
    if not MODEL_PATH.exists():
        train_model()
    with MODEL_PATH.open("rb") as handle:
        return pickle.load(handle)


def synthetic_reading(mode: str, seed: int) -> tuple[dict[str, float], np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    anomaly = mode in {"watch", "critical"}
    persistent = mode == "critical"
    vibration = make_window(72 if anomaly else 12, 0.30 if anomaly else 0.035, 0.01 if anomaly else 0.004, seed)
    acoustic = make_window(112 if persistent else 38, 0.72 if persistent else 0.12, 0.02 if persistent else 0.012, seed + 1000)
    reading = {
        "vibration": float(np.max(np.abs(vibration))),
        "acoustic": float(55 + (35 if persistent else 0)),
        "pressure": float(1014 - (22 if persistent else 0) + rng.normal(0, 0.4)),
        "temperature": float(22 + rng.normal(0, 0.4)),
        "strain": float(1160 if persistent else 900 + rng.normal(0, 4)),
    }
    return reading, vibration, acoustic


def classify(model, vibration: np.ndarray, acoustic: np.ndarray, reading: dict[str, float]) -> dict[str, bool]:
    vector = np.asarray([feature_vector(vibration, acoustic)])
    ml_anomaly = bool(model.predict(vector)[0] == -1)
    vibration_anomaly = ml_anomaly and reading["vibration"] > 0.12
    acoustic_anomaly = ml_anomaly and reading["acoustic"] > 70
    pressure_anomaly = reading["pressure"] < 1000
    strain_anomaly = reading["strain"] > 1050
    return {
        "ml": ml_anomaly,
        "vibration": vibration_anomaly,
        "acoustic": acoustic_anomaly,
        "pressure": pressure_anomaly,
        "strain": strain_anomaly,
    }


def append_row(reading: dict[str, float], status: str, output_path: Path = CSV_PATH) -> dict[str, str]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    needs_header = not output_path.exists() or output_path.stat().st_size == 0
    row = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        "vibration": f"{reading['vibration']:.4f}",
        "acoustic": f"{reading['acoustic']:.1f}",
        "pressure": f"{reading['pressure']:.1f}",
        "temperature": f"{reading['temperature']:.1f}",
        "strain": f"{reading['strain']:.1f}",
        "status": status,
    }
    with output_path.open("a", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        if needs_header:
            writer.writeheader()
        writer.writerow(row)
    return row


def process(mode: str, state_machine: StateMachine, model, seed: int, output_path: Path = CSV_PATH) -> dict[str, str]:
    reading, vibration, acoustic = synthetic_reading(mode, seed)
    flags = classify(model, vibration, acoustic, reading)
    status = state_machine.update(flags)
    return append_row(reading, status, output_path)


def run_demo(output_path: Path = CSV_PATH) -> None:
    model = load_model()
    machine = StateMachine()
    steps = [("normal", 2), ("watch", 1), ("critical", 2), ("normal", 1)]
    seeds = {"normal": 600, "watch": 500, "critical": 800}
    for mode, count in steps:
        for index in range(count):
            row = process(mode, machine, model, seeds[mode], output_path)
            print(f"{row['status']} | {mode} | vibration={row['vibration']} acoustic={row['acoustic']}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["normal", "watch", "critical"], default="normal")
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--output", type=Path, default=CSV_PATH)
    args = parser.parse_args()
    if args.demo:
        run_demo(args.output)
    else:
        row = process(args.mode, StateMachine(), load_model(), 600, args.output)
        print(f"{row['status']} | {args.mode} | vibration={row['vibration']} acoustic={row['acoustic']}")
