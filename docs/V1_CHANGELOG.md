# Sentinel V1 Changelog

This changelog records repository history and the verified V1 restoration/validation work. Dates are included only where available from Git history or the verification record.

## 2026-09-16 - Initial software scaffold

- Added the backend Node/Express scaffold and mock telemetry generator.
- Added the first React dashboard.
- Connected event history and the existing test-alert flow to the backend.
- Completed the initial dashboard hardening work.

Source commits: `775a4d5`, `887d9dd`, `35372a7`, `9ab9e8a`.

## 2026-09-18 - Frontend and repository alignment

- Converted the frontend from TypeScript to JavaScript.
- Updated repository documentation and the dashboard/API integration presentation.
- Added the current camera placeholder, development SMS script, and API risk presentation fields.

Source commits: `b71c2c0`, `54e0748`, `21eb843`.

## 2026-09-19 - V1 pipeline restoration and environment verification

- Restored the missing V1 Python processing surfaces:
  - FFT feature extraction.
  - Synthetic baseline calibration.
  - Isolation Forest training and persistence.
  - State machine and multi-sensor fusion.
  - Synthetic sensor pipeline and CSV logging.
- Added `backend/requirements.txt` and a persisted `backend/models/isolation_forest.pkl`.
- Changed the Node mock launcher to invoke the Python pipeline instead of assigning random statuses.
- Added CSV parsing cleanup in Express for Python-generated line endings.
- Added the automated `backend/tests/test_v1.py` suite.
- Repaired and verified the Python 3 virtual environment and Node dependencies.
- Verified the deterministic demo sequence:

```text
NORMAL -> WATCH -> CRITICAL -> NORMAL
```

- Verified Express endpoints, API-to-CSV consistency, frontend build, browser dashboard integration, and repeatability.
- Added the V1 documentation package under `docs/`.

## V1 freeze status

The V1 software demonstration is verified as a synthetic, local architecture. Real Jetson sensors, field calibration, physical GSM delivery, and real camera capture remain future work.
