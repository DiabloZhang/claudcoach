from datetime import datetime, timezone
from types import SimpleNamespace

from analysis.anomalies import detect_anomalies, scan_all_anomalies


def make_activity(
    sport_type="Run",
    moving_time=3600,
    elapsed_time=3600,
    distance=10000,
    tss=None,
    is_excluded=False,
    exclude_reason=None,
    start_date=None,
    id=1,
    strava_id=101,
    name="Morning Run",
):
    return SimpleNamespace(
        sport_type=sport_type,
        moving_time=moving_time,
        elapsed_time=elapsed_time,
        distance=distance,
        tss=tss,
        is_excluded=is_excluded,
        exclude_reason=exclude_reason,
        start_date=start_date or datetime.now(timezone.utc),
        id=id,
        strava_id=strava_id,
        name=name,
    )


class TestDetectAnomalies:
    def test_normal_activity(self):
        act = make_activity("Run", moving_time=3600, distance=10000)
        assert detect_anomalies(act) == []

    def test_swim_pace_too_fast(self):
        # 1000m in 30s -> 3s/100m，明显异常
        act = make_activity("Swim", moving_time=30, distance=1000)
        reasons = detect_anomalies(act)
        assert any("游泳配速异常" in r for r in reasons)

    def test_swim_distance_too_long(self):
        act = make_activity("Swim", moving_time=3600, distance=25000)
        reasons = detect_anomalies(act)
        assert any("游泳距离异常" in r for r in reasons)

    def test_ride_speed_too_fast(self):
        # 100km in 1h -> 100km/h
        act = make_activity("Ride", moving_time=3600, distance=100000)
        reasons = detect_anomalies(act)
        assert any("骑行时速异常" in r for r in reasons)

    def test_run_pace_too_fast(self):
        # 1000m in 150s -> 2:30/km
        act = make_activity("Run", moving_time=150, distance=1000)
        reasons = detect_anomalies(act)
        assert any("跑步配速异常" in r for r in reasons)

    def test_tss_too_high(self):
        act = make_activity("Ride", moving_time=3600, distance=30000, tss=450)
        reasons = detect_anomalies(act)
        assert any("TSS异常" in r for r in reasons)

    def test_duration_too_long(self):
        act = make_activity("Run", moving_time=20 * 3600, distance=100000)
        reasons = detect_anomalies(act)
        assert any("时长异常" in r for r in reasons)

    def test_zero_distance_with_duration(self):
        act = make_activity("Run", moving_time=1200, distance=0)
        reasons = detect_anomalies(act)
        assert any("距离为0" in r for r in reasons)

    def test_zero_distance_ignored_for_non_gps_sport(self):
        act = make_activity("Yoga", moving_time=1200, distance=0)
        reasons = detect_anomalies(act)
        assert not any("距离为0" in r for r in reasons)

    def test_openwater_uses_swim_rules(self):
        act = make_activity("OpenWater", moving_time=30, distance=1000)
        reasons = detect_anomalies(act)
        assert any("游泳配速异常" in r for r in reasons)

    def test_virtualride_uses_ride_rules(self):
        act = make_activity("VirtualRide", moving_time=3600, distance=100000)
        reasons = detect_anomalies(act)
        assert any("骑行时速异常" in r for r in reasons)

    def test_tss_none_does_not_crash(self):
        act = make_activity("Run", moving_time=3600, distance=10000, tss=None)
        assert detect_anomalies(act) == []


class TestScanAllAnomalies:
    def test_mixed_activities(self):
        normal = make_activity("Run", id=1, strava_id=1, distance=10000)
        bad = make_activity("Ride", id=2, strava_id=2, distance=100000)
        flagged = scan_all_anomalies([normal, bad])
        assert len(flagged) == 1
        assert flagged[0]["id"] == 2
        assert "anomaly_reasons" in flagged[0]

    def test_all_normal(self):
        acts = [make_activity("Run", id=i, strava_id=i) for i in range(3)]
        assert scan_all_anomalies(acts) == []

    def test_flagged_fields(self):
        bad = make_activity("Swim", id=3, strava_id=3, distance=25000, is_excluded=True, exclude_reason="test")
        flagged = scan_all_anomalies([bad])
        assert flagged[0]["is_excluded"] is True
        assert flagged[0]["exclude_reason"] == "test"
        assert flagged[0]["distance_km"] == 25.0
