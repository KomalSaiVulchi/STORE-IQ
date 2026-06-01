"""Unit tests for anomaly detection."""
# PROMPT: Add tests for new anomaly types: DEAD_ZONE, CAMERA_OFFLINE, CROWD_ALERT.
# CHANGES MADE: Added tests for the new anomaly types.

from anomaly.anomaly_engine import AnomalyEngine


def test_queue_spike_warn():
    """Queue spike should return WARN for z > 2."""
    engine = AnomalyEngine()
    baseline = [10, 11, 9, 10, 12, 9, 11]
    result = engine.queue_spike(current=16, baseline=baseline)
    assert result is not None
    assert result.severity in {"WARN", "CRITICAL"}


def test_conversion_drop_critical():
    """Conversion drop should return CRITICAL for < 50% of weekly avg."""
    engine = AnomalyEngine()
    result = engine.conversion_drop(current=2, weekly_avg=6)
    assert result is not None
    assert result.severity == "CRITICAL"


def test_dead_zone_critical():
    """Dead zone should return CRITICAL if zero visits for 60+ minutes."""
    engine = AnomalyEngine()
    result = engine.dead_zone(zone_visits=0, minutes=65, zone_id="MAKEUP")
    assert result is not None
    assert result.severity == "CRITICAL"
    assert result.zone_id == "MAKEUP"

def test_dead_zone_warn():
    """Dead zone should return WARN if zero visits for 30+ minutes."""
    engine = AnomalyEngine()
    result = engine.dead_zone(zone_visits=0, minutes=35, zone_id="HAIRCARE")
    assert result is not None
    assert result.severity == "WARN"
    assert result.zone_id == "HAIRCARE"


def test_camera_offline():
    """Camera offline for >10 mins should return CRITICAL."""
    engine = AnomalyEngine()
    result = engine.camera_offline(minutes=15, camera_id="cam_01")
    assert result is not None
    assert result.severity == "CRITICAL"
    assert "cam_01" in result.reason


def test_crowd_alert():
    """Crowd alert should trigger at 85% and 95% capacity."""
    engine = AnomalyEngine()
    result_warn = engine.crowd_alert(current=90, capacity=100)
    assert result_warn is not None
    assert result_warn.severity == "WARN"

    result_crit = engine.crowd_alert(current=96, capacity=100)
    assert result_crit is not None
    assert result_crit.severity == "CRITICAL"
