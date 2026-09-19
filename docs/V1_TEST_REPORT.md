# Sentinel V1 Test Report

## 1. Report Control

| Field | Value |
|---|---|
| Project | Sentinel |
| Scope | V1 software-only demonstration |
| Test date | 2026-09-19 |
| Environment | Linux, Python 3.12.3, Node.js v24.21.0, npm 11.19.0 |
| Python environment | `backend/.venv` |
| Result | PASS |

## 2. Test Objectives

- Verify the actual FFT feature implementation.
- Verify Isolation Forest training, persistence, and inference.
- Verify multi-sensor state transitions and recovery.
- Verify deterministic synthetic normal and anomaly scenarios.
- Verify CSV integrity and API consistency.
- Verify Express endpoints and React build/integration.
- Verify repeatability of the complete V1 flow.

## 3. Environment Evidence

Verified imports from `backend/.venv`:

| Package | Verified version |
|---|---:|
| Python | 3.12.3 |
| NumPy | 2.5.3 |
| SciPy | 1.18.1 |
| scikit-learn | 1.9.1 |
| joblib | 1.6.0 |
| pytest | 9.1.1 |
| Node.js | v24.21.0 |
| npm | 11.19.0 |

## 4. Test Case Results

| ID | Component | Test | Expected | Actual | Status |
|---|---|---|---|---|---|
| V1-FFT-001 | FFT | Extract features from deterministic 8 Hz signal | Five finite features; dominant frequency near 8 Hz | Feature keys and finite values verified; dominant frequency matched | PASS |
| V1-FFT-002 | FFT | Extract features from deterministic 31 Hz signal | Dominant frequency differs substantially from normal signal | 31 Hz signal classified at the expected frequency | PASS |
| V1-FFT-003 | FFT validation | Reject short, NaN, infinite, and invalid-rate inputs | Raise `ValueError` | All invalid-input cases raised `ValueError` | PASS |
| V1-ML-001 | Calibration | Train Isolation Forest | Model file created and loadable | `backend/models/isolation_forest.pkl` created and loaded | PASS |
| V1-ML-002 | Inference | Predict deterministic normal and anomalous feature vectors | Valid predictions; anomaly prediction is `-1` | Predictions and decision scores verified | PASS |
| V1-STATE-001 | State machine | Normal, single anomaly, persistent multi-sensor anomaly, recovery | `NORMAL -> WATCH -> CRITICAL -> NORMAL` | Required sequence verified | PASS |
| V1-PIPE-001 | Pipeline | Run normal mode | One valid NORMAL row | Valid NORMAL row written | PASS |
| V1-PIPE-002 | Pipeline | Run deterministic demo | `NORMAL,NORMAL,WATCH,CRITICAL,CRITICAL,NORMAL` | Exact sequence produced | PASS |
| V1-CSV-001 | CSV | Validate header, rows, numeric fields, and statuses | Parseable V1 contract | All rows and fields validated | PASS |
| V1-API-001 | Express | GET `/api/telemetry` | HTTP 200, JSON latest row | HTTP 200 and valid telemetry returned | PASS |
| V1-API-002 | Express | GET `/api/events` | HTTP 200, newest-first event array | HTTP 200 and event history returned | PASS |
| V1-API-003 | Express | POST `/api/test-alert` | HTTP 200, success JSON | HTTP 200 and `success: true` returned | PASS |
| V1-API-004 | Integration | Compare latest API telemetry with CSV | Same latest reading | Timestamp and status matched | PASS |
| V1-FE-001 | Frontend | Install dependencies and build | Vite build succeeds | `npm run build` completed successfully | PASS |
| V1-FE-002 | Frontend/API | Inspect REST endpoints and polling | Existing Express paths used; no WebSockets | `/api/telemetry`, `/api/events`, and `/api/test-alert` verified | PASS |
| V1-E2E-001 | End-to-end | Run pipeline, Express, API, and frontend build | Complete chain works | Automated smoke flow passed | PASS |
| V1-E2E-002 | Repeatability | Repeat complete automated flow | Same deterministic state behavior | Full suite passed twice with 10 tests each | PASS |

## 5. Commands Executed

Environment and dependencies:

```bash
python3 --version
python3 -m pip --version
python3 -m venv backend/.venv
backend/.venv/bin/python -m pip install -r backend/requirements.txt
backend/.venv/bin/python -c "import numpy as np; print('NUMPY OK:', np.__version__)"
npm install --prefix backend
npm install --prefix frontend --no-package-lock
```

Application paths:

```bash
backend/.venv/bin/python backend/fft_features.py
backend/.venv/bin/python backend/baseline_calibration.py
backend/.venv/bin/python backend/state_machine.py
backend/.venv/bin/python backend/sensor_pipeline.py --demo --output /tmp/sentinel-v1-env.csv
SENTINEL_DEMO=1 node backend/mock_data/generate_mock.js
npm run build --prefix frontend
```

Automated suite:

```bash
backend/.venv/bin/python -m pytest -q
```

The suite returned `10 passed` on both verification runs. A live API run returned the latest status `NORMAL`, 20 event records, and a successful test-alert response. The browser dashboard rendered online telemetry, charts, and event history.

## 6. Observations

- The model is trained on synthetic normal data and is appropriate only for this V1 demonstration.
- `sensor_log.csv` is intentionally ignored by Git and is generated at runtime.
- The test-alert route executes the existing development SMS script; no physical GSM delivery was tested.
- The camera endpoint serves the generated placeholder JPEG rather than a physical camera frame.
- No hardware, database, FastAPI, or WebSocket component was included in this test scope.
