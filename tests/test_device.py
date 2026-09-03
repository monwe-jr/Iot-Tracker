import device


def test_defect_alert_when_voltage_low_and_frequency_high(monkeypatch):
    monkeypatch.setattr(device.random, "uniform", lambda a, b: 1.5)
    monkeypatch.setattr(device.random, "choice", lambda seq: 400)

    reading = device.generate_parametric_sweep()

    assert reading["status"] == "DEFECT_ALERT"


def test_stable_when_voltage_high_even_at_high_frequency(monkeypatch):
    monkeypatch.setattr(device.random, "uniform", lambda a, b: 3.3)
    monkeypatch.setattr(device.random, "choice", lambda seq: 800)

    reading = device.generate_parametric_sweep()

    assert reading["status"] == "STABLE"


def test_stable_when_voltage_low_but_frequency_below_threshold(monkeypatch):
    monkeypatch.setattr(device.random, "uniform", lambda a, b: 1.5)
    monkeypatch.setattr(device.random, "choice", lambda seq: 200)

    reading = device.generate_parametric_sweep()

    assert reading["status"] == "STABLE"
