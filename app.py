import json
import os
from contextlib import asynccontextmanager

import asyncpg
import redis.asyncio as redis
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from pydantic import BaseModel, Field

POSTGRES_DSN = (
    f"postgresql://{os.getenv('POSTGRES_USER', 'postgres')}:"
    f"{os.getenv('POSTGRES_PASSWORD', 'postgres')}@"
    f"{os.getenv('POSTGRES_HOST', 'localhost')}/"
    f"{os.getenv('POSTGRES_DB', 'telemetry_db')}"
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"), port=6379, decode_responses=True
    )
    app.state.db_pool = await asyncpg.create_pool(POSTGRES_DSN)
    async with app.state.db_pool.acquire() as conn:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS hardware_logs (
                id SERIAL PRIMARY KEY,
                device_id VARCHAR(50),
                timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                voltage_v NUMERIC(4,2),
                frequency_mhz INT,
                temperature_c NUMERIC(4,1),
                status VARCHAR(20)
            );
            """
        )
    yield
    await app.state.db_pool.close()
    await app.state.redis.aclose()


app = FastAPI(title="IoT Telemetry Ingestion Engine", lifespan=lifespan)


def get_redis(request: Request) -> redis.Redis:
    return request.app.state.redis


def get_db_pool(request: Request) -> asyncpg.Pool:
    return request.app.state.db_pool


class TelemetrySchema(BaseModel):
    device_id: str
    timestamp: float
    voltage_v: float = Field(ge=0.0, le=12.0, description="Supply voltage in volts")
    frequency_mhz: int = Field(ge=0, le=10_000, description="Clock frequency in MHz")
    temperature_c: float = Field(
        ge=-40.0, le=150.0, description="Die temperature in Celsius"
    )
    status: str


@app.post("/api/telemetry")
async def ingest_telemetry(
    data: TelemetrySchema,
    redis_client: redis.Redis = Depends(get_redis),
    pool: asyncpg.Pool = Depends(get_db_pool),
):
    try:
        # 1. Write to Redis Cache for Ultra-Low Latency UI Reads
        cache_payload = json.dumps(data.model_dump())
        await redis_client.set(f"live_status:{data.device_id}", cache_payload)

        # 2. Persist to PostgreSQL for historical parametric analysis
        async with pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO hardware_logs (device_id, voltage_v, frequency_mhz, temperature_c, status)
                   VALUES ($1, $2, $3, $4, $5)""",
                data.device_id,
                data.voltage_v,
                data.frequency_mhz,
                data.temperature_c,
                data.status,
            )

        return {"status": "success", "cached": True, "persisted": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/telemetry/live/{device_id}")
async def get_live_telemetry(
    device_id: str, redis_client: redis.Redis = Depends(get_redis)
):
    """Fetches real-time status instantly from Redis cache"""
    cached_data = await redis_client.get(f"live_status:{device_id}")
    if not cached_data:
        raise HTTPException(status_code=404, detail="Device data not found in live cache.")
    return json.loads(cached_data)


@app.get("/api/telemetry/history/{device_id}")
async def get_telemetry_history(
    device_id: str,
    limit: int = Query(default=50, ge=1, le=500),
    pool: asyncpg.Pool = Depends(get_db_pool),
):
    """Fetches the most recent historical readings for a device from PostgreSQL"""
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT device_id, timestamp, voltage_v, frequency_mhz, temperature_c, status
               FROM hardware_logs
               WHERE device_id = $1
               ORDER BY timestamp DESC
               LIMIT $2""",
            device_id,
            limit,
        )

    if not rows:
        raise HTTPException(
            status_code=404, detail="No historical data found for this device."
        )

    return [
        {
            "device_id": row["device_id"],
            "timestamp": row["timestamp"].isoformat(),
            "voltage_v": float(row["voltage_v"]),
            "frequency_mhz": row["frequency_mhz"],
            "temperature_c": float(row["temperature_c"]),
            "status": row["status"],
        }
        for row in rows
    ]
