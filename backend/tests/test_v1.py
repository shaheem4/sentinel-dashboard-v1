from __future__ import annotations

import csv
import json
import pickle
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import numpy as np
import pytest

BACKEND = Path(__file__).resolve().parents[1]
FRONTEND = BACKEND.parent / "frontend"
CSV_PATH = BACKEND / "mock_data" / "sensor_log.csv"

sys.path.insert(0, str(BACKEND))

from baseline_calibration import (  # noqa: E402
    FEATURE_NAMES,
    MODEL_FEATURE_NAMES,
    build_training_data,
    feature_vector,
    make_window,
    train_model,
)
from fft_features import extract_features  # noqa: E402
from sensor_pipeline import process, synthetic_reading  # noqa: E402
from state_machine import StateMachine  # noqa: E402


def sine_wave(frequency: float, sample_rate: float = 100.0, samples: int = 1000) -> np.ndarray:
    time_values = np.arange(samples) / sample_rate
    return np.sin(2 * np.pi * frequency * time_values)


def run_demo(output_path: Path) -> list[dict[str, str]]:
    result = subprocess.run(
        [sys.executable, str(BACKEND / "sensor_pipeline.py"), "--demo", "--output", str(output_path)],
        cwd=BACKEND,
        check=True,
        capture_output=True,
        text=True,
    )
    rows = list(csv.DictReader(output_path.open(newline="")))
    assert result.stdout.splitlines()[-1].startswith("NORMAL | normal")
    return rows


def test_fft_features_normal_and_anomalous_signals() -> None:
    normal = extract_features(sine_wave(8.0), 100.0)
    anomalous = extract_features(sine_wave(31.0), 100.0)

    assert set(FEATURE_NAMES) <= normal.keys()
    assert all(np.isfinite(list(normal.values())))
    assert normal["rms"] > 0
    assert normal["peak_amplitude"] > 0
    assert abs(normal["dominant_frequency"] - 8.0) < 0.2
    assert abs(anomalous["dominant_frequency"] - 31.0) < 0.2
    assert abs(normal["dominant_frequency"] - anomalous["dominant_frequency"]) > 10


def test_fft_rejects_invalid_inputs() -> None:
    with pytest.raises(ValueError):
        extract_features([1.0], 100.0)
    with pytest.raises(ValueError):
        extract_features([0.0, np.nan], 100.0)
    with pytest.raises(ValueError):
        extract_features([0.0, np.inf], 100.0)
    with pytest.raises(ValueError):
        extract_features([0.0, 1.0], 0.0)
    with pytest.raises(ValueError):
        extract_features([0.0, 1.0], -10.0)


def test_isolation_forest_training_and_model_metadata(tmp_path: Path) -> None:
    output_path = tmp_path / "isolation_forest.pkl"
    trained_path = train_model(output_path)
    assert trained_path.exists()
    with trained_path.open("rb") as handle:
        model = pickle.load(handle)
    assert model.modalities == ("vibration", "acoustic")
    assert tuple(model.feature_names) == MODEL_FEATURE_NAMES
    assert all(any(name in feature_name for feature_name in model.feature_names) for name in FEATURE_NAMES)
    assert build_training_data().shape[1] == len(MODEL_FEATURE_NAMES)


def test_actual_isolation_forest_inference(tmp_path: Path) -> None:
    model_path = train_model(tmp_path / "model.pkl")
    with model_path.open("rb") as handle:
        model = pickle.load(handle)

    normal_vibration = make_window(12, 0.035, 0.004, 600)
    normal_acoustic = make_window(38, 0.12, 0.012, 1600)
    anomalous_vibration = make_window(72, 0.30, 0.01, 500)
    anomalous_acoustic = make_window(112, 0.72, 0.02, 1500)
    normal_prediction = model.predict([feature_vector(normal_vibration, normal_acoustic)])[0]
    anomaly_prediction = model.predict([feature_vector(anomalous_vibration, anomalous_acoustic)])[0]
    normal_score = model.decision_function([feature_vector(normal_vibration, normal_acoustic)])[0]
    anomaly_score = model.decision_function([feature_vector(anomalous_vibration, anomalous_acoustic)])[0]

    assert normal_prediction in {-1, 1}
    assert anomaly_prediction in {-1, 1}
    assert anomaly_prediction == -1
    assert anomaly_score < normal_score


def test_state_machine_fusion_and_validation() -> None:
    machine = StateMachine(critical_persistence=2)
    assert machine.update({}) == "NORMAL"
    assert machine.update({"vibration": True}) == "WATCH"
    assert machine.update({"vibration": True, "acoustic": True}) == "WATCH"
    assert machine.update({"vibration": True, "acoustic": True}) == "CRITICAL"
    assert machine.update({}) == "NORMAL"

    for invalid in (0, -1, True, 1.5):
        with pytest.raises(ValueError):
            StateMachine(invalid)


def test_normal_pipeline_writes_valid_row(tmp_path: Path) -> None:
    output_path = tmp_path / "normal.csv"
    result = subprocess.run(
        [sys.executable, str(BACKEND / "sensor_pipeline.py"), "--mode", "normal", "--output", str(output_path)],
        cwd=BACKEND,
        check=True,
        capture_output=True,
        text=True,
    )
    rows = list(csv.DictReader(output_path.open(newline="")))
    assert result.stdout.startswith("NORMAL | normal")
    assert len(rows) == 1
    assert rows[0]["status"] == "NORMAL"


def test_anomaly_pipeline_reaches_critical_and_recovers(tmp_path: Path) -> None:
    rows = run_demo(tmp_path / "demo.csv")
    assert [row["status"] for row in rows] == ["NORMAL", "NORMAL", "WATCH", "CRITICAL", "CRITICAL", "NORMAL"]


def test_csv_integrity_after_demo(tmp_path: Path) -> None:
    output_path = tmp_path / "integrity.csv"
    rows = run_demo(output_path)
    required = {"timestamp", "vibration", "acoustic", "pressure", "temperature", "strain", "status"}
    assert output_path.exists()
    assert set(rows[0]) == required
    assert len(rows) >= 2
    for row in rows:
        assert row["timestamp"].endswith("Z")
        for field in required - {"timestamp", "status"}:
            assert np.isfinite(float(row[field]))
        assert row["status"] in {"NORMAL", "WATCH", "CRITICAL"}


def test_frontend_uses_existing_rest_contract() -> None:
    app_source = (FRONTEND / "src" / "App.jsx").read_text()
    assert "http://localhost:5000/api/telemetry" in app_source
    assert "http://localhost:5000/api/events" in app_source
    assert "http://localhost:5000/api/test-alert" in app_source
    assert "setInterval(fetchTelemetry, 2000)" in app_source


def request_json(url: str, method: str = "GET"):
    request = urllib.request.Request(url, method=method)
    with urllib.request.urlopen(request, timeout=5) as response:
        assert response.status == 200
        return json.load(response)


def wait_for_server(url: str) -> None:
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            request_json(url)
            return
        except (OSError, urllib.error.URLError):
            time.sleep(0.1)
    raise AssertionError("Express server did not start")


def test_complete_smoke_twice_and_api_consistency(tmp_path: Path) -> None:
    original_csv = CSV_PATH.read_bytes() if CSV_PATH.exists() else None
    server = None
    try:
        first_rows = run_demo(tmp_path / "run1.csv")
        second_rows = run_demo(tmp_path / "run2.csv")
        comparable_fields = ["vibration", "acoustic", "pressure", "temperature", "strain", "status"]
        assert [[row[field] for field in comparable_fields] for row in first_rows] == [
            [row[field] for field in comparable_fields] for row in second_rows
        ]
        CSV_PATH.write_bytes((tmp_path / "run2.csv").read_bytes())
        server = subprocess.Popen(["node", "server.js"], cwd=BACKEND, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        wait_for_server("http://127.0.0.1:5000/api/telemetry")

        telemetry = request_json("http://127.0.0.1:5000/api/telemetry")
        events = request_json("http://127.0.0.1:5000/api/events")
        alert = request_json("http://127.0.0.1:5000/api/test-alert", "POST")
        latest = second_rows[-1]
        assert telemetry["timestamp"] == latest["timestamp"]
        assert telemetry["status"] == latest["status"]
        assert len(events) == len(second_rows)
        assert [event["status"] for event in reversed(events)] == [row["status"] for row in second_rows]
        assert alert["success"] is True

        build = subprocess.run(["npm", "run", "build"], cwd=FRONTEND, capture_output=True, text=True)
        assert build.returncode == 0, build.stdout + build.stderr
    finally:
        if server is not None:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()
        if original_csv is None:
            CSV_PATH.unlink(missing_ok=True)
        else:
            CSV_PATH.write_bytes(original_csv)
