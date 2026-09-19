# Sentinel V1 Team Setup

This guide brings up the verified software-only V1 demonstration. It uses Python 3, Express, and the existing React/Vite dashboard.

## Prerequisites

- Linux/macOS/Windows environment with Python 3, Node.js, and npm.
- Node.js 18 or newer is the documented repository prerequisite.
- No physical sensor, Jetson, database, or external service is required.

## 1. Clone and enter the repository

```bash
git clone https://github.com/Vineet890/sentinel-dashboard.git
cd sentinel-dashboard
```

## 2. Create the Python environment

```bash
python3 -m venv backend/.venv
```

Use the explicit environment executable for every Python command:

```bash
backend/.venv/bin/python --version
backend/.venv/bin/python -m pip --version
```

## 3. Install Python dependencies

```bash
backend/.venv/bin/python -m pip install -r backend/requirements.txt
backend/.venv/bin/python -c "import numpy as np; print('NUMPY OK:', np.__version__)"
backend/.venv/bin/python -c "import sklearn, joblib, pytest; print('PYTHON IMPORTS OK')"
```

## 4. Install Node dependencies

```bash
npm install --prefix backend
npm install --prefix frontend --no-package-lock
```

The frontend repository retains `pnpm-lock.yaml`; the command above was used for the verified npm-based setup without creating a second frontend lockfile.

## 5. Generate the V1 model and demo data

From the repository root:

```bash
backend/.venv/bin/python backend/baseline_calibration.py
SENTINEL_DEMO=1 node backend/mock_data/generate_mock.js
```

The demo writes `backend/mock_data/sensor_log.csv` and produces:

```text
NORMAL -> WATCH -> CRITICAL -> NORMAL
```

The CSV is ignored by Git and can be regenerated.

## 6. Run the tests

```bash
backend/.venv/bin/python -m pytest -q
```

The verified suite contains 10 tests and passed twice during V1 verification.

## 7. Start the backend

In a terminal from the repository root:

```bash
node backend/server.js
```

The API listens on `http://localhost:5000`.

## 8. Start the frontend

In another terminal:

```bash
cd frontend
npm run dev
```

The dashboard listens on `http://localhost:8443`.

## 9. Verify the dashboard

Open `http://localhost:8443/`. The dashboard should show the latest CSV telemetry, system status, charts, and event history. The browser calls the Express endpoints at `http://localhost:5000`.

Useful API checks:

```bash
curl http://localhost:5000/api/telemetry
curl http://localhost:5000/api/events
curl -X POST http://localhost:5000/api/test-alert
```

## Troubleshooting

- If NumPy cannot be imported, run the `backend/.venv/bin/python -m pip install -r backend/requirements.txt` command again and repeat the import check.
- If telemetry fails, generate at least one row with `SENTINEL_DEMO=1 node backend/mock_data/generate_mock.js` before starting Express.
- If port 5000 or 8443 is busy, stop the unrelated process before starting V1.
- The test-alert route is a development flow. It does not verify physical GSM delivery.
- The camera image in V1 is a generated placeholder, not a physical camera feed.
