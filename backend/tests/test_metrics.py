import pytest
from datetime import date, timedelta
from types import SimpleNamespace

from analysis.metrics import (
    calc_cycling_tss,
    calc_running_tss,
    calc_swimming_tss,
    calc_tss_for_activity,
    calc_ctl_atl_tsb,
    calc_hr_zone_distribution,
    calc_triathlon_balance,
)


class TestCalcCyclingTss:
    def test_normal_case(self):
        tss = calc_cycling_tss(duration_seconds=3600, normalized_power=200, avg_power=190, ftp=250)
        # IF = 200/250 = 0.8; TSS = 3600 * 200 * 0.8 / (250 * 3600) * 100 = 64.0
        assert tss == 64.0

    def test_missing_ftp(self):
        assert calc_cycling_tss(3600, 200, 190, None) is None

    def test_missing_power(self):
        assert calc_cycling_tss(3600, None, None, 250) is None

    def test_uses_avg_power_when_no_np(self):
        tss = calc_cycling_tss(3600, None, 200, 250)
        assert tss == 64.0


class TestCalcRunningTss:
    def test_pace_method(self):
        # threshold 4:00/km = 240s, avg pace 5:00/km = 300s
        # IF = 240/300 = 0.8; TSS = 3600 * 0.64 / 3600 * 100 = 64.0
        tss = calc_running_tss(3600, avg_pace_s_per_km=300, threshold_pace_s_per_km=240, avg_hr=150, lthr=170)
        assert tss == 64.0

    def test_hr_fallback(self):
        # IF = 150/170 ≈ 0.882; TSS = 1800 * 0.882^2 / 3600 * 100 ≈ 38.9
        tss = calc_running_tss(1800, None, None, avg_hr=150, lthr=170)
        assert tss is not None
        assert round(tss, 1) == round(1800 * (150 / 170) ** 2 / 3600 * 100, 1)

    def test_no_data(self):
        assert calc_running_tss(3600, None, None, None, None) is None


class TestCalcSwimmingTss:
    def test_normal_case(self):
        # 1000m in 20min (1200s) -> pace = 120s/100m
        # CSS = 120s/100m -> IF = 1.0 -> TSS = 1200 * 1 / 3600 * 100 = 33.3
        tss = calc_swimming_tss(duration_seconds=1200, distance_meters=1000, css_s_per_100m=120)
        assert tss == pytest.approx(33.3, rel=1e-2)

    def test_missing_distance(self):
        assert calc_swimming_tss(1200, 0, 120) is None

    def test_missing_css(self):
        assert calc_swimming_tss(1200, 1000, None) is None


class TestCalcTssForActivity:
    def make_activity(self, sport_type, **kwargs):
        defaults = dict(
            moving_time=3600,
            elapsed_time=3600,
            normalized_power=None,
            avg_power=None,
            avg_pace=None,
            avg_heart_rate=None,
            distance=None,
        )
        defaults.update(kwargs)
        return SimpleNamespace(sport_type=sport_type, **defaults)

    def make_user(self, ftp=None, lthr=None, css=None, run_threshold_pace=None):
        return SimpleNamespace(ftp=ftp, lthr=lthr, css=css, run_threshold_pace=run_threshold_pace)

    def test_ride(self):
        act = self.make_activity("Ride", avg_power=200)
        user = self.make_user(ftp=250)
        assert calc_tss_for_activity(act, user) == 64.0

    def test_run_by_pace(self):
        act = self.make_activity("Run", avg_pace=300)
        user = self.make_user(run_threshold_pace=240)
        assert calc_tss_for_activity(act, user) == 64.0

    def test_swim(self):
        act = self.make_activity("Swim", moving_time=1200, distance=1000)
        user = self.make_user(css=120)
        assert calc_tss_for_activity(act, user) == pytest.approx(33.3, rel=1e-2)

    def test_zero_duration(self):
        act = self.make_activity("Ride", moving_time=0, elapsed_time=0, avg_power=200)
        user = self.make_user(ftp=250)
        assert calc_tss_for_activity(act, user) is None

    def test_unknown_sport_with_hr(self):
        act = self.make_activity("Yoga", avg_heart_rate=140)
        user = self.make_user(lthr=170)
        assert calc_tss_for_activity(act, user) is not None


class TestCalcCtlAtlTsb:
    def test_empty_input(self):
        result = calc_ctl_atl_tsb({}, end_date=date(2026, 4, 1), days=7)
        assert len(result) == 7
        for r in result:
            assert r["ctl"] == 0.0
            assert r["atl"] == 0.0
            assert r["tsb"] == 0.0

    def test_single_day(self):
        daily = {date(2026, 4, 1): 100}
        result = calc_ctl_atl_tsb(daily, end_date=date(2026, 4, 1), days=1)
        assert len(result) == 1
        # 函数内部对结果做了 round(..., 1)
        assert result[0]["ctl"] == round(100 / 42, 1)
        assert result[0]["atl"] == round(100 / 7, 1)

    def test_consecutive_days_convergence(self):
        # 连续 100 TSS 很多天后，CTL 应趋近于 100
        daily = {date(2026, 1, 1) + timedelta(days=i): 100 for i in range(200)}
        # 需要计算全部 200 天才能看到收敛
        result = calc_ctl_atl_tsb(daily, end_date=date(2026, 1, 1) + timedelta(days=199), days=200)
        last = result[-1]
        assert last["ctl"] == pytest.approx(100.0, abs=2.0)
        assert last["atl"] == pytest.approx(100.0, abs=2.0)
        assert last["tsb"] == pytest.approx(0.0, abs=1.0)


class TestCalcHrZoneDistribution:
    def test_empty_stream(self):
        assert calc_hr_zone_distribution([], lthr=170) == []

    def test_distribution(self):
        # LTHR=170; Z1 < 144.5, Z2 144.5-151.3, Z3 151.3-159.8, Z4 159.8-170, Z5 >=170
        stream = [140, 150, 160, 170, 180]
        zones = calc_hr_zone_distribution(stream, lthr=170)
        assert len(zones) == 5
        # 140->0.823(Z1), 150->0.882(Z2), 160->0.941(Z4), 170->1.00(Z5), 180->1.058(Z5)
        assert zones[0]["seconds"] == 1  # Z1
        assert zones[1]["seconds"] == 1  # Z2
        assert zones[2]["seconds"] == 0  # Z3
        assert zones[3]["seconds"] == 1  # Z4
        assert zones[4]["seconds"] == 2  # Z5
        for z in zones:
            assert z["percent"] == pytest.approx(z["seconds"] / 5 * 100, rel=1e-3)

    def test_none_values_ignored(self):
        stream = [140, None, 180]
        zones = calc_hr_zone_distribution(stream, lthr=170)
        total = sum(z["seconds"] for z in zones)
        assert total == 2


class TestCalcTriathlonBalance:
    def make_activity(self, sport_type, start_date, moving_time=3600, distance=10000):
        return SimpleNamespace(sport_type=sport_type, start_date=start_date, moving_time=moving_time, distance=distance)

    def test_balance(self):
        today = date.today()
        activities = [
            self.make_activity("Swim", today, moving_time=1800, distance=1000),
            self.make_activity("Ride", today, moving_time=7200, distance=30000),
            self.make_activity("Run", today, moving_time=3600, distance=10000),
            self.make_activity("Run", today - timedelta(days=40), moving_time=3600, distance=10000),  # 过期，应忽略
        ]
        balance = calc_triathlon_balance(activities, days=28)
        assert balance["swim"]["count"] == 1
        assert balance["bike"]["count"] == 1
        assert balance["run"]["count"] == 1
        assert balance["swim"]["duration_min"] == 30.0
        assert balance["bike"]["distance_km"] == 30.0

    def test_no_activities(self):
        balance = calc_triathlon_balance([], days=28)
        for sport in ("swim", "bike", "run"):
            assert balance[sport]["count"] == 0

    def test_start_date_as_string_or_datetime(self):
        # 兼容 start_date 为 date 对象的情况（SQLAlchemy 实际返回 datetime）
        act = SimpleNamespace(sport_type="Run", start_date=date.today(), moving_time=3600, distance=10000)
        balance = calc_triathlon_balance([act], days=28)
        assert balance["run"]["count"] == 1
