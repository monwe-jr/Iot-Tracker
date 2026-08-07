# IoT Telemetry Ingestion Engine

A real-time telemetry ingestion pipeline for simulated hardware devices. A Python device emulator streams parametric voltage/frequency sweep data at 1Hz to a FastAPI service, which caches live state in Redis for low-latency reads and persists historical records to PostgreSQL for analysis.

## Architecture

```
device.py  --HTTP POST-->  FastAPI (app.py)  -->  Redis (live cache)
                                              -->  PostgreSQL (historical log)
```

- **`device.py`** — simulates a hardware device (`STM32-ASIC-TEST-01`), generating randomized voltage, frequency, and temperature readings once per second, including simulated defect conditions when voltage drops below 1.8V at frequencies ≥400MHz.
- **`app.py`** — FastAPI service that ingests telemetry, writes the latest reading per device to Redis, and appends every reading to a PostgreSQL log table.
- **`docker-compose.yml`** — spins up the API, Redis, and PostgreSQL together.

## Requirements

- Docker and Docker Compose
- Python 3.10+ (only needed to run `device.py` outside a container)

## Getting Started

1. **Start the stack:**
   ```bash
   docker-compose up --build
   ```
   This launches the API on `localhost:8000`, Redis on `6379`, and PostgreSQL on `5432`.

2. **Run the device simulator** (in a separate terminal):
   ```bash
   pip install -r requirements.txt
   python device.py
   ```
   This streams simulated telemetry to the API once per second.

## API Endpoints

### `POST /api/telemetry`
Ingests a telemetry reading and writes it to both Redis and PostgreSQL.

**Body:**
```json
{
  "device_id": "STM32-ASIC-TEST-01",
  "timestamp": 1735689600.0,
  "voltage_v": 3.3,
  "frequency_mhz": 400,
  "temperature_c": 45.2,
  "status": "STABLE"
}
```

### `GET /api/telemetry/live/{device_id}`
Returns the most recent cached reading for a given device from Redis.

## Environment Variables

Set automatically by `docker-compose.yml` when running via Compose:

| Variable | Default | Purpose |
|---|---|---|
| `REDIS_HOST` | `localhost` | Redis hostname |
| `POSTGRES_HOST` | `localhost` | PostgreSQL hostname |
| `POSTGRES_DB` | `telemetry_db` | Database name |
| `POSTGRES_USER` | `postgres` | Database user |
| `POSTGRES_PASSWORD` | `postgres` | Database password |

## Known Issues

- `app.py` is missing an `import json` statement, required by both the ingestion and live-read endpoints.
- The 404 response in `GET /api/telemetry/live/{device_id}` passes an invalid `block_reason` argument to `HTTPException` instead of `detail`.
- Pinned versions in `requirements.txt` should be verified against actually published PyPI releases before deploying.

These are tracked for a fix; see the project issues or reach out before relying on this in production.

## Project Structure

```
.
├── app.py               # FastAPI ingestion service
├── device.py             # Simulated hardware telemetry emitter
├── docker-compose.yml    # Service orchestration (API, Redis, PostgreSQL)
└── requirements.txt       # Python dependencies
```
