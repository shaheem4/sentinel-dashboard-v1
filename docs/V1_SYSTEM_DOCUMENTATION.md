# Sentinel V1 System Documentation

## A. Document Control

| Field | Value |
|---|---|
| Project | Sentinel |
| Release | V1 software demonstration |
| Documentation version | 1.0 |
| Status | Verified software baseline |
| Purpose | Technical record and maintenance reference for the V1 mock demonstration |
| Last verified | 2026-09-19 |
| Repository | `https://github.com/Vineet890/sentinel-dashboard` |
| Intended audience | Sentinel developers, evaluators, and V2 integration team |

This document describes the implementation currently present in the repository. It does not describe unimplemented hardware capabilities as if they were operational.

## B. Executive Summary

Sentinel V1 is a local, software-only mine-subsidence monitoring demonstration. It generates deterministic synthetic vibration and acoustic windows, extracts FFT-derived features, classifies the combined feature vector with a persisted scikit-learn Isolation Forest, derives anomaly flags, and applies a temporal multi-sensor state machine. Each processed reading is appended to a CSV file. An Express server reads that CSV and exposes REST endpoints consumed by a React dashboard.

The verified demonstration produces the sequence `NORMAL -> WATCH -> CRITICAL -> NORMAL` without physical sensors, a database, WebSockets, or FastAPI.

## C. Problem Statement

The project addresses the Smart India Hackathon problem of AI-enabled, low-cost mine-subsidence monitoring and early warning for underground coal mines. V1 demonstrates the software decision path that can later receive real sensor inputs. It is not a field deployment and does not claim to measure a real mine site.

## D. V1 Scope

### Implemented

- Deterministic synthetic vibration and acoustic signal windows.
- NumPy FFT feature extraction.
- Five features per modality: RMS, peak amplitude, dominant frequency, spectral centroid, and zero-crossing rate.
- Isolation Forest training, persistence, loading, and inference.
- Derived anomaly flags for ML, vibration, acoustic, pressure, and strain.
- NORMAL, WATCH, and CRITICAL temporal state logic.
- CSV logging with the V1 telemetry schema.
- Express REST API on port 5000.
- React/Vite dashboard on port 8443.
- Automated Python tests covering the pipeline and API smoke flow.

### Not implemented in V1

- Real Jetson or sensor I/O.
- LIS3DH, ADXL345, BMP280, INMP441, or IMX219 integration.
- Real baseline calibration from field data.
- Database persistence.
- FastAPI or WebSockets.
- Production GSM dispatch. The existing test-alert route invokes the development SMS script and reports a successful development fallback in this environment.
- Real camera capture. The mock generator creates a minimal placeholder JPEG for the existing dashboard image slot.

## E. System Architecture

```text
Synthetic sensor data
        |
        v
Sensor pipeline
        |
        v
FFT feature extraction
        |
        v
Isolation Forest
        |
        v
Anomaly flags
        |
        v
State machine / sensor fusion
        |
        v
CSV logging
        |
        v
Express REST API
        |
        v
React dashboard
```

### Components

1. **Synthetic data**: `sensor_pipeline.py` creates deterministic normal, watch, and critical windows using seeded NumPy random generators and sine waves.
2. **Feature extraction**: `fft_features.py` calculates the five features for one signal window.
3. **Model**: `baseline_calibration.py` builds normal vibration/acoustic training windows, scales the ten-value combined vector, and trains an `IsolationForest`.
4. **Anomaly flags**: `sensor_pipeline.py` calls the saved model and combines its prediction with demonstration thresholds for vibration, acoustic, pressure, and strain.
5. **Fusion/state**: `state_machine.py` counts anomalous modalities and requires persistence before entering CRITICAL.
6. **Storage**: `sensor_pipeline.py` appends rows to `backend/mock_data/sensor_log.csv`.
7. **API**: `backend/server.js` reads the CSV and serves telemetry, events, camera placeholder data, and the existing test-alert route.
8. **UI**: `frontend/src/App.jsx` polls telemetry and events every two seconds and displays state, charts, event history, and dashboard controls.

## F. Repository Structure

```text
sentinel-v1/
├── backend/
│   ├── baseline_calibration.py       # Synthetic baseline and Isolation Forest training
│   ├── fft_features.py               # FFT feature extraction
│   ├── requirements.txt              # Python dependencies
│   ├── sensor_pipeline.py            # Synthetic processing, flags, state, CSV output
│   ├── state_machine.py              # NORMAL/WATCH/CRITICAL logic
│   ├── server.js                     # Express REST API
│   ├── package.json                  # Backend Node dependencies
│   ├── package-lock.json             # Backend npm lockfile
│   ├── models/
│   │   └── isolation_forest.pkl      # Persisted trained model
│   ├── mock_data/
│   │   ├── generate_mock.js          # Node launcher for repeated synthetic readings
│   │   ├── sensor_log.csv            # Runtime CSV output; ignored by Git
│   │   └── latest_capture.jpg        # Runtime placeholder; ignored by Git
│   ├── scripts/
│   │   └── send_sms.py               # Development/hardware-boundary alert script
│   └── tests/
│       └── test_v1.py                # Automated V1 verification suite
├── frontend/
│   ├── package.json                  # React/Vite dependencies and scripts
│   ├── pnpm-lock.yaml                # Frontend pnpm lockfile
│   ├── vite.config.js                # Vite configuration, port 8443
│   └── src/
│       ├── App.jsx                   # Dashboard and REST polling
│       ├── main.jsx                  # React entry point
│       └── index.css                 # Dashboard styles and animations
├── .gitignore
└── README.md
```

Generated directories such as `.venv/`, `node_modules/`, `frontend/dist/`, `__pycache__/`, and pytest cache are local environment outputs and are not part of the application architecture.

## G. Python Environment

V1 requires Python 3.12 or a compatible Python 3 release. The verified environment is `backend/.venv`.

Direct requirements in `backend/requirements.txt`:

- `numpy`: signal arrays, FFT operations, and deterministic synthetic data.
- `scikit-learn`: `StandardScaler`, `Pipeline`, and `IsolationForest`.
- `pytest`: automated tests.

`scipy` and `joblib` are installed transitively by scikit-learn and were verified in the tested environment. They are not directly imported by the application modules.

From the repository root:

```bash
python3 -m venv backend/.venv
backend/.venv/bin/python -m pip install -r backend/requirements.txt
backend/.venv/bin/python -c "import numpy as np; print('NUMPY OK:', np.__version__)"
backend/.venv/bin/python -c "import sklearn, joblib, pytest; print('ML TEST IMPORTS OK')"
```

Use `backend/.venv/bin/python` for all V1 Python commands. Do not use a bare `python` command.

## H. Machine Learning Pipeline

`baseline_calibration.py` creates 160 seeded normal training examples. Each example contains one vibration window and one acoustic window. The five features from each modality are concatenated into a ten-value vector.

The trained model is a scikit-learn `Pipeline`:

```text
StandardScaler -> IsolationForest
```

The Isolation Forest uses 200 estimators, `contamination=0.05`, and `random_state=42`. It is serialized with `pickle` to `backend/models/isolation_forest.pkl`. `sensor_pipeline.py` loads that file and trains it automatically if the file is absent.

Inference uses `model.predict()`. A prediction of `-1` is treated as an ML anomaly. The model result is combined with the demonstration sensor conditions to create modality flags; statuses are then assigned by the state machine, not randomly.

## I. Feature Engineering

The same five features are calculated for vibration and acoustic windows:

| Feature | Practical meaning |
|---|---|
| `rms` | Overall signal energy or magnitude over the window. |
| `peak_amplitude` | Largest absolute sample value in the window. |
| `dominant_frequency` | Frequency bin with the strongest positive-frequency FFT magnitude. |
| `spectral_centroid` | Magnitude-weighted center of the positive-frequency spectrum. |
| `zero_crossing_rate` | Fraction of adjacent samples whose sign changes. |

`fft_features.py` rejects windows shorter than two samples, non-finite values, and non-positive sample rates.

## J. Alert and State Logic

`StateMachine` starts in `NORMAL` and defaults to `critical_persistence=2`.

- **NORMAL**: no anomaly flags are present.
- **WATCH**: at least one anomaly flag is present, or a multi-sensor anomaly has not yet persisted long enough.
- **CRITICAL**: at least two anomaly flags are present and remain present for the configured persistence count.
- **Recovery**: a clear reading with no anomaly flags returns the state to `NORMAL`, including from CRITICAL.

The implementation counts truthy values in the complete flag mapping. In the pipeline, the flags are `ml`, `vibration`, `acoustic`, `pressure`, and `strain`. A single-sensor anomaly cannot immediately become CRITICAL. The deterministic demo uses normal readings, one watch reading, two persistent critical readings, and a final normal reading.

## K. Synthetic Sensor Pipeline

`sensor_pipeline.py` supports `--mode normal`, `--mode watch`, `--mode critical`, and `--demo`. Its default output is `backend/mock_data/sensor_log.csv`; tests and demos can supply `--output` for an isolated file.

- Normal windows use low-amplitude vibration around 12 Hz and low-amplitude acoustic data around 38 Hz.
- Watch windows use elevated vibration around 72 Hz while acoustic and environmental values remain near normal.
- Critical windows use elevated vibration, acoustic level 90, reduced pressure, and strain 1160.
- Seeds make the demonstration repeatable.

The Node launcher `backend/mock_data/generate_mock.js` invokes the local `.venv` pipeline every two seconds. With `SENTINEL_DEMO=1`, it runs the complete deterministic demo once.

Example demonstration command:

```bash
cd backend
SENTINEL_DEMO=1 node mock_data/generate_mock.js
```

Expected status sequence:

```text
NORMAL, NORMAL, WATCH, CRITICAL, CRITICAL, NORMAL
```

## L. Data Contract

The CSV header is:

```text
timestamp,vibration,acoustic,pressure,temperature,strain,status
```

| Field | Meaning | Type in CSV | Example | Source |
|---|---|---|---|---|
| `timestamp` | UTC processing time | ISO 8601 string | `2026-09-19T02:00:00.000Z` | `append_row()` |
| `vibration` | Peak synthetic vibration magnitude | Decimal string | `0.0424` | Vibration window |
| `acoustic` | Synthetic acoustic level | Decimal string | `55.0` | Synthetic reading logic |
| `pressure` | Synthetic pressure value | Decimal string | `1013.8` | Synthetic reading logic |
| `temperature` | Synthetic temperature value | Decimal string | `22.0` | Synthetic reading logic |
| `strain` | Synthetic strain/load value | Decimal string | `897.0` | Synthetic reading logic |
| `status` | State-machine output | Enum string | `NORMAL` | `StateMachine.update()` |

Express returns these CSV values as strings and adds `uptime`, `risk_score`, and `risk_label` to `/api/telemetry`. The risk fields are API presentation values calculated from vibration, acoustic, and strain; they are separate from the CSV state-machine status.

## M. Express API

Server: `node backend/server.js`, listening on `http://localhost:5000`.

### GET `/api/telemetry`

Reads the last CSV row and returns it as a JSON object. It also adds server uptime and a heuristic risk score/label.

Example response:

```json
{
  "timestamp": "2026-09-19T02:00:00.000Z",
  "vibration": "0.0424",
  "acoustic": "55.0",
  "pressure": "1013.8",
  "temperature": "22.0",
  "strain": "897.0",
  "status": "NORMAL",
  "uptime": "0d 0h",
  "risk_score": "0.15",
  "risk_label": "LOW"
}
```

Errors while reading the file return HTTP 500 with `{ "error": "Failed to read telemetry" }`.

### GET `/api/events`

Reads the last 20 CSV rows and returns them newest first. Each event contains the CSV fields. Errors return HTTP 500 with `{ "error": "Failed to read events" }`.

### POST `/api/test-alert`

Takes no request body. The current implementation executes `backend/scripts/send_sms.py` through `python3`. In development, that script logs a development/fallback message because physical GSM hardware is not present. The route returns a successful JSON response so the dashboard flow remains testable.

Possible successful responses include:

```json
{
  "success": true,
  "message": "SMS dispatched via SIM900A",
  "mode": "hardware"
}
```

The `hardware` label reflects the current route branch and script execution, not verified physical GSM delivery. Execution failures fall back to a successful logged-alert response.

### GET `/api/camera`

This route exists in the current server and serves `latest_capture.jpg` when present. The V1 generator creates a 1x1 placeholder JPEG; no real camera capture is implemented.

## N. Frontend

The frontend is React 19 with Vite and Recharts. It runs on port 8443. `frontend/src/App.jsx` polls:

- `http://localhost:5000/api/telemetry` every two seconds.
- `http://localhost:5000/api/events` every two seconds.
- `http://localhost:5000/api/test-alert` when the dashboard alert button is used.
- `/api/camera` for the existing image slot.

The dashboard displays status, sensor charts, event history, connection state, uptime, risk presentation fields, and a manual demonstration state control already present in the UI. It does not use WebSockets.

Build command:

```bash
cd frontend
npm install --no-package-lock
npm run build
```

## O. Testing

The automated suite is `backend/tests/test_v1.py` and was executed with:

```bash
backend/.venv/bin/python -m pytest -q
```

The verified result on 2026-09-19 was `10 passed`, repeated successfully. Coverage includes:

- Normal and anomalous FFT feature extraction.
- Invalid FFT input validation.
- Isolation Forest training, metadata, persistence, and inference.
- State-machine persistence, fusion, recovery, and constructor validation.
- Normal pipeline output.
- Deterministic anomaly sequence.
- CSV schema and numeric integrity.
- Frontend REST contract inspection.
- Two-run smoke flow with Express telemetry/events/alert, API-to-CSV consistency, and frontend build.

Additional manual verification executed the standalone FFT, calibration, state-machine, pipeline, Express API, and browser dashboard paths.

## P. Known Limitations

- All sensor input is synthetic and deterministic; no physical sensor is read.
- The training baseline is synthetic and is not a real mine-site calibration.
- Demonstration amplitudes and environmental thresholds are software-demo values.
- CSV is the only persistence layer and is not designed for concurrent production writers.
- Express parses the simple comma-separated contract and does not provide authentication or schema versioning.
- The test-alert route does not prove GSM delivery. The camera asset is a placeholder.
- The API risk score is a heuristic presentation field and should not be confused with the Isolation Forest decision.
- The current V1 development environment requires Node.js/npm and Python package installation; deployment packaging is not yet provided.

## Q. V2 Integration Plan

These are future boundaries, not V1 features:

1. Add Jetson Nano acquisition and deployment orchestration.
2. Map real accelerometer, acoustic, pressure, temperature, and strain inputs to the existing pipeline contract.
3. Evaluate LIS3DH or ADXL345 vibration hardware, BMP280 environmental sensing, and INMP441 audio input.
4. Integrate IMX219 camera capture separately from the V1 placeholder.
5. Replace synthetic calibration with controlled baseline collection and validation.
6. Add sensor health/failure diagnostics and field-safe recovery behavior.
7. Integrate GSM hardware and verify delivery independently of the test-alert route.
8. Preserve the REST/CSV boundary initially; evaluate storage and transport changes only as a separate milestone.
9. Validate offline operation and Jetson resource constraints.

## R. Troubleshooting

### NumPy or sklearn import failure

Use the repository environment explicitly:

```bash
python3 -m venv backend/.venv
backend/.venv/bin/python -m pip install -r backend/requirements.txt
backend/.venv/bin/python -c "import numpy as np; print('NUMPY OK:', np.__version__)"
```

Do not use a bare `python` or `pip` command.

### Model file missing

Run:

```bash
backend/.venv/bin/python backend/baseline_calibration.py
```

This creates `backend/models/isolation_forest.pkl`.

### Backend cannot read telemetry

Generate at least one CSV row before starting Express:

```bash
cd backend
SENTINEL_DEMO=1 node mock_data/generate_mock.js
node server.js
```

### Port already in use

Stop the old Node/Vite process or use the existing configured ports only after confirming the old process is unrelated. The V1 defaults are backend 5000 and frontend 8443.

### Frontend dependency/build failure

From `frontend/`, run `npm install --no-package-lock` and then `npm run build`. The repository uses `pnpm-lock.yaml`; do not add a second frontend lockfile unless the package-management policy changes.

## S. Reproducibility

From a fresh clone:

```bash
git clone https://github.com/Vineet890/sentinel-dashboard.git
cd sentinel-dashboard
python3 -m venv backend/.venv
backend/.venv/bin/python -m pip install -r backend/requirements.txt
npm install --prefix backend
npm install --prefix frontend --no-package-lock
backend/.venv/bin/python backend/baseline_calibration.py
SENTINEL_DEMO=1 node backend/mock_data/generate_mock.js
```

Start the services in separate terminals:

```bash
node backend/server.js
```

```bash
cd frontend
npm run dev
```

Run verification:

```bash
backend/.venv/bin/python -m pytest -q
```

Open `http://localhost:8443/` after the backend and at least one generated CSV row are available.

## T. Verification Checklist

- [x] Python 3 environment created and verified.
- [x] Python dependencies installed.
- [x] NumPy import verified.
- [x] FFT extraction and invalid-input validation verified.
- [x] Isolation Forest model generated and loaded.
- [x] State machine verified.
- [x] Normal synthetic pipeline verified.
- [x] Anomaly synthetic pipeline verified.
- [x] CSV schema and values verified.
- [x] Express endpoints verified.
- [x] API-to-CSV consistency verified.
- [x] Frontend dependency installation and build verified.
- [x] Browser dashboard integration verified.
- [x] End-to-end suite passed twice.
