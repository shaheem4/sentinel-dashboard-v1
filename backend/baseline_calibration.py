"""Train and persist the V1 Isolation Forest on synthetic normal windows."""

from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from fft_features import FEATURE_NAMES, extract_features

MODEL_PATH = Path(__file__).resolve().parent / "models" / "isolation_forest.pkl"
SAMPLE_RATE = 256
WINDOW_SIZE = 256
MODEL_FEATURE_NAMES = tuple(
    f"{modality}_{name}"
    for modality in ("vibration", "acoustic")
    for name in FEATURE_NAMES
)


def make_window(frequency: float, amplitude: float, noise: float, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    time = np.arange(WINDOW_SIZE) / SAMPLE_RATE
    return amplitude * np.sin(2 * np.pi * frequency * time) + rng.normal(0, noise, WINDOW_SIZE)


def feature_vector(vibration: np.ndarray, acoustic: np.ndarray) -> list[float]:
    vibration_features = extract_features(vibration, SAMPLE_RATE)
    acoustic_features = extract_features(acoustic, SAMPLE_RATE)
    return [vibration_features[name] for name in FEATURE_NAMES] + [acoustic_features[name] for name in FEATURE_NAMES]


def build_training_data(samples: int = 160) -> np.ndarray:
    rows = []
    for seed in range(samples):
        vibration = make_window(12 + seed % 4, 0.035 + (seed % 5) * 0.003, 0.004, seed)
        acoustic = make_window(38 + seed % 5, 0.12 + (seed % 4) * 0.01, 0.012, seed + 1000)
        rows.append(feature_vector(vibration, acoustic))
    return np.asarray(rows)


def train_model(output_path: Path = MODEL_PATH) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    model = Pipeline([
        ("scaler", StandardScaler()),
        ("isolation_forest", IsolationForest(n_estimators=200, contamination=0.05, random_state=42)),
    ])
    model.fit(build_training_data())
    model.feature_names = MODEL_FEATURE_NAMES
    model.modalities = ("vibration", "acoustic")
    with output_path.open("wb") as handle:
        pickle.dump(model, handle)
    return output_path


if __name__ == "__main__":
    path = train_model()
    print(f"trained Isolation Forest with features: {', '.join(FEATURE_NAMES)}")
    print(f"saved model: {path}")
