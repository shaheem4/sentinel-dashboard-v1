"""FFT-derived features used by the synthetic Sentinel pipeline."""

from __future__ import annotations

import json
import sys
from typing import Iterable

import numpy as np

FEATURE_NAMES = (
    "rms",
    "peak_amplitude",
    "dominant_frequency",
    "spectral_centroid",
    "zero_crossing_rate",
)


def extract_features(signal: Iterable[float], sample_rate: float) -> dict[str, float]:
    """Return the five features used by the anomaly model."""
    values = np.asarray(tuple(signal), dtype=float)
    if values.size < 2:
        raise ValueError("signal must contain at least two samples")
    if not np.all(np.isfinite(values)):
        raise ValueError("signal must contain only finite values")
    if sample_rate <= 0:
        raise ValueError("sample_rate must be positive")

    spectrum = np.abs(np.fft.rfft(values))
    frequencies = np.fft.rfftfreq(values.size, d=1.0 / sample_rate)
    nonzero = frequencies > 0
    weighted_total = float(spectrum[nonzero].sum())
    dominant_index = int(np.argmax(spectrum[nonzero])) if weighted_total else 0
    positive_frequencies = frequencies[nonzero]
    positive_spectrum = spectrum[nonzero]

    return {
        "rms": float(np.sqrt(np.mean(values ** 2))),
        "peak_amplitude": float(np.max(np.abs(values))),
        "dominant_frequency": float(positive_frequencies[dominant_index]) if weighted_total else 0.0,
        "spectral_centroid": float(np.sum(positive_frequencies * positive_spectrum) / weighted_total) if weighted_total else 0.0,
        "zero_crossing_rate": float(np.count_nonzero(np.diff(np.signbit(values))) / (values.size - 1)),
    }


def _demo_signal() -> np.ndarray:
    time = np.arange(256) / 256.0
    return 0.25 * np.sin(2 * np.pi * 32 * time)


if __name__ == "__main__":
    print(json.dumps(extract_features(_demo_signal(), 256), indent=2, sort_keys=True))
