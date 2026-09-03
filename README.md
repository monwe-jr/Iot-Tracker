# IoT Telemetry Ingestion Engine

A real-time telemetry ingestion pipeline for simulated hardware devices. A Python device emulator streams parametric voltage/frequency sweep data at 1Hz to a FastAPI service, which caches live state in Redis for low-latency reads and persists historical records to PostgreSQL for analysis.

## Architecture

```
device.py  --HTTP POST-->  FastAPI (app.py)  -->  Redis (live cache)
                                              -->  PostgreSQL (historical log)
```

- **`device.py`** — simulates a hardware device (`STM32-ASIC-TEST-01`), generating randomized voltage, frequency, and temperature readings once per second, including simulated defect conditions when voltage drops below 1.8V at frequencies ≥400MHz.
- **`app.py`** — FastAPI service that ingests telemetry, writes the latest reading per device to Redis, and appends every reading to a PostgreSQL log table. All I/O uses async drivers (`asyncpg`, `redis.asyncio`) so requests don't block the event loop.
- **`docker-compose.yml`** — spins up the API, Redis, and PostgreSQL together.

## Requirements

- Docker and Docker Compose
- Python 3.10+ (only needed to run `device.py`, or the app, outside a container)

## Getting Started

1. **Configure environment variables:**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and set a real `POSTGRES_PASSWORD`. `.env` is gitignored — never commit real credentials.

2. **Start the stack:**
   ```bash
   docker-compose up --build
   ```
   This launches the API on `localhost:8000`, Redis on `6379`, and PostgreSQL on `5432`.

3. **Run the device simulator** (in a separate terminal):
   ```bash
   pip install -r requirements.txt
   python device.py
   ```
   This streams simulated telemetry to the API once per second.

## Running tests

```bash
pip install -r requirements-dev.txt
pytest
```

The test suite mocks Redis and PostgreSQL, so it runs without a live stack.

## API Endpoints

### `POST /api/telemetry`
Ingests a telemetry reading and writes it to both Redis and PostgreSQL. `voltage_v`, `frequency_mhz`, and `temperature_c` are bounds-checked (0–12V, 0–10000MHz, -40–150°C) and reject out-of-range values with a `422`.

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
Returns the most recent cached reading for a given device from Redis. Returns `404` if nothing has been cached for that device yet.

### `GET /api/telemetry/history/{device_id}`
Returns recent historical readings for a device from PostgreSQL, most recent first. Accepts an optional `limit` query parameter (default `50`, max `500`). Returns `404` if no readings exist for that device.

```bash
curl "http://localhost:8000/api/telemetry/history/STM32-ASIC-TEST-01?limit=10"
```

## Environment Variables

Read from `.env` by `docker-compose.yml` (see `.env.example`):

| Variable | Purpose |
|---|---|
| `POSTGRES_DB` | Database name |
| `POSTGRES_USER` | Database user |
| `POSTGRES_PASSWORD` | Database password |

`REDIS_HOST` and `POSTGRES_HOST` are set directly in `docker-compose.yml` to the service names (`redis_cache`, `postgres_db`); override them if running the app outside Compose.

## Known Issues

None currently tracked. If you hit something, open an issue.

## Project Structure

```
.
├── app.py                  # FastAPI ingestion service
├── device.py                # Simulated hardware telemetry emitter
├── docker-compose.yml       # Service orchestration (API, Redis, PostgreSQL)
├── Dockerfile                # API container image
├── requirements.txt          # Runtime dependencies
├── requirements-dev.txt      # Test dependencies
├── .env.example               # Template for local environment variables
└── tests/                      # pytest suite
```
