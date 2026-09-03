SAMPLE_PAYLOAD = {
    "device_id": "STM32-ASIC-TEST-01",
    "timestamp": 1735689600.0,
    "voltage_v": 3.3,
    "frequency_mhz": 400,
    "temperature_c": 45.2,
    "status": "STABLE",
}


def test_ingest_telemetry_success(client):
    response = client.post("/api/telemetry", json=SAMPLE_PAYLOAD)

    assert response.status_code == 200
    assert response.json() == {"status": "success", "cached": True, "persisted": True}


def test_ingest_telemetry_rejects_out_of_range_voltage(client):
    payload = {**SAMPLE_PAYLOAD, "voltage_v": 999.0}

    response = client.post("/api/telemetry", json=payload)

    assert response.status_code == 422


def test_get_live_telemetry_returns_cached_reading(client):
    client.post("/api/telemetry", json=SAMPLE_PAYLOAD)

    response = client.get(f"/api/telemetry/live/{SAMPLE_PAYLOAD['device_id']}")

    assert response.status_code == 200
    assert response.json()["device_id"] == SAMPLE_PAYLOAD["device_id"]


def test_get_live_telemetry_404_when_device_unknown(client):
    response = client.get("/api/telemetry/live/UNKNOWN-DEVICE")

    assert response.status_code == 404


def test_get_telemetry_history_returns_recent_readings(client):
    client.post("/api/telemetry", json=SAMPLE_PAYLOAD)
    client.post("/api/telemetry", json={**SAMPLE_PAYLOAD, "status": "DEFECT_ALERT"})

    response = client.get(f"/api/telemetry/history/{SAMPLE_PAYLOAD['device_id']}")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert body[0]["status"] == "DEFECT_ALERT"  # most recent first


def test_get_telemetry_history_404_when_device_unknown(client):
    response = client.get("/api/telemetry/history/UNKNOWN-DEVICE")

    assert response.status_code == 404
