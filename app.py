import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import redis
import psycopg2
from psycopg2.extras import RealDictCursor

app = FastAPI(title="IoT Telemetry Ingestion Engine")

# Initialize Connections (Configs mapped from Docker-Compose environment)
r = redis.Redis(host=os.getenv("REDIS_HOST", "localhost"), port=6379, decode_responses=True)

def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        database=os.getenv("POSTGRES_DB", "telemetry_db"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "postgres")
    )

class TelemetrySchema(BaseModel):
    device_id: str
    timestamp: float
    voltage_v: float
    frequency_mhz: int
    temperature_c: float
    status: str

@app.on_event("startup")
def setup_db():
    """Initializes the database schema if it doesn't exist"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS hardware_logs (
            id SERIAL PRIMARY KEY,
            device_id VARCHAR(50),
            timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            voltage_v NUMERIC(4,2),
            frequency_mhz INT,
            temperature_c NUMERIC(4,1),
            status VARCHAR(20)
        );
    """)
    conn.commit()
    cur.close()
    conn.close()

@app.post("/api/telemetry")
async def ingest_telemetry(data: TelemetrySchema):
    try:
        # 1. Write to Redis Cache for Ultra-Low Latency UI Reads
        cache_payload = json.dumps(data.dict())
        r.set(f"live_status:{data.device_id}", cache_payload)
        
        # 2. Persist to PostgreSQL for historical parametric analysis
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO hardware_logs (device_id, voltage_v, frequency_mhz, temperature_c, status) 
               VALUES (%s, %s, %s, %s, %s)""",
            (data.device_id, data.voltage_v, data.frequency_mhz, data.temperature_c, data.status)
        )
        conn.commit()
        cur.close()
        conn.close()
        
        return {"status": "success", "cached": True, "persisted": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/telemetry/live/{device_id}")
async def get_live_telemetry(device_id: str):
    """Fetches real-time status instantly from Redis cache"""
    cached_data = r.get(f"live_status:{device_id}")
    if not cached_data:
        raise HTTPException(status_code=404, block_reason="Device data not found in live cache.")
    return json.loads(cached_data)