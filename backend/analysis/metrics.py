"""
训练指标计算引擎
- TSS（训练压力分）：骑行用功率，跑步/游泳用心率或配速
- CTL / ATL / TSB：体能/疲劳/状态指数（指数加权移动平均）
- 心率区间分布（Z1-Z5，基于 LTHR）
- 三项训练量平衡
"""

from datetime import date, timedelta
from typing import Optional
import math


# ─────────────────────────────────────────
# TSS 计算
# ─────────────────────────────────────────

def calc_cycling_tss(
    duration_seconds: int,
    normalized_power: Optional[float],
    avg_power: Optional[float],
    ftp: Optional[float],
) -> Optional[float]:
    """
    骑行 TSS = (duration × NP × IF) / (FTP × 3600) × 100
    IF = NP / FTP
    """
    if not ftp or ftp <= 0:
        return None
    np = normalized_power or avg_power
    if not np or np <= 0:
        return None
    intensity_factor = np / ftp
    tss = (duration_seconds * np * intensity_factor) / (ftp * 3600) * 100
    return round(tss, 1)


def calc_running_tss(
    duration_seconds: int,
    avg_pace_s_per_km: Optional[float],     # 秒/km，越小越快
    threshold_pace_s_per_km: Optional[float],
    avg_hr: Optional[float],
    lthr: Optional[float],
) -> Optional[float]:
    """
    优先用配速（rTSS），其次用心率（hrTSS）。
    rTSS: IF = threshold_pace / avg_pace，TSS = duration × IF² / 3600 × 100
    hrTSS: IF = avg_hr / LTHR，TSS = duration × IF² / 3600 × 100
    """
    # 优先：配速法
    if avg_pace_s_per_km and threshold_pace_s_per_km and avg_pace_s_per_km > 0:
        intensity_factor = threshold_pace_s_per_km / avg_pace_s_per_km
        tss = duration_seconds * (intensity_factor ** 2) / 3600 * 100
        return round(tss, 1)
    # 备选：心率法
    if avg_hr and lthr and lthr > 0:
        intensity_factor = avg_hr / lthr
        tss = duration_seconds * (intensity_factor ** 2) / 3600 * 100
        return round(tss, 1)
    return None


def calc_swimming_tss(
    duration_seconds: int,
    distance_meters: Optional[float],       # 游泳距离（米）
    css_s_per_100m: Optional[float],        # 临界游泳速度（秒/100m）
) -> Optional[float]:
    """
    swTSS: 先算平均配速（s/100m），IF = CSS / swim_pace，TSS = duration × IF² / 3600 × 100
    """
    if not distance_meters or distance_meters <= 0:
        return None
    if not css_s_per_100m or css_s_per_100m <= 0:
        return None
    swim_pace = (duration_seconds / distance_meters) * 100  # 秒/100m
    if swim_pace <= 0:
        return None
    intensity_factor = css_s_per_100m / swim_pace
    tss = duration_seconds * (intensity_factor ** 2) / 3600 * 100
    return round(tss, 1)


def calc_tss_for_activity(activity, user) -> Optional[float]:
    """
    根据运动类型选择计算方法，返回 TSS 或 None（缺少阈值参数时）。
    """
    sport = (activity.sport_type or "").lower()
    duration = activity.moving_time or activity.elapsed_time or 0

    if duration <= 0:
        return None

    if sport in ("ride", "virtualride", "ebikeride"):
        return calc_cycling_tss(
            duration,
            activity.normalized_power,
            activity.avg_power,
            user.ftp,
        )
    elif sport in ("run", "trailrun", "treadmill"):
        return calc_running_tss(
            duration,
            activity.avg_pace,
            user.run_threshold_pace,
            activity.avg_heart_rate,
            user.lthr,
        )
    elif sport in ("swim", "openwater"):
        return calc_swimming_tss(
            duration,
            activity.distance,
            user.css,
        )
    else:
        # 其他运动（力量/瑜伽等）：用心率法兜底
        if activity.avg_heart_rate and user.lthr:
            return calc_running_tss(
                duration,
                None, None,
                activity.avg_heart_rate,
                user.lthr,
            )
        return None


# ─────────────────────────────────────────
# CTL / ATL / TSB
# ─────────────────────────────────────────

def calc_ctl_atl_tsb(daily_tss: dict[date, float], end_date: date, days: int = 90):
    """
    计算最近 `days` 天的 CTL/ATL/TSB 时序数据。

    daily_tss: {date: tss_value}（只需包含有训练的天）
    返回: [{"date": ..., "ctl": ..., "atl": ..., "tsb": ...}, ...]
    """
    CTL_DAYS = 42   # 慢性训练负荷，42天加权
    ATL_DAYS = 7    # 急性训练负荷，7天加权

    ctl_k = 1.0 / CTL_DAYS
    atl_k = 1.0 / ATL_DAYS

    start_date = end_date - timedelta(days=days - 1)

    ctl = 0.0
    atl = 0.0
    result = []

    current = start_date
    while current <= end_date:
        tss_today = daily_tss.get(current, 0.0)
        # 指数加权：new = old × (1 - k) + tss × k
        ctl = ctl * (1 - ctl_k) + tss_today * ctl_k
        atl = atl * (1 - atl_k) + tss_today * atl_k
        tsb = ctl - atl

        result.append({
            "date": current.isoformat(),
            "ctl": round(ctl, 1),
            "atl": round(atl, 1),
            "tsb": round(tsb, 1),
            "tss": round(tss_today, 1),
        })
        current += timedelta(days=1)

    return result


# ─────────────────────────────────────────
# 心率区间分布（基于 LTHR）
# ─────────────────────────────────────────

HR_ZONES = [
    ("Z1 恢复",    0,     0.85),
    ("Z2 有氧",    0.85,  0.89),
    ("Z3 节奏",    0.89,  0.94),
    ("Z4 乳酸阈",  0.94,  1.00),
    ("Z5 无氧",    1.00,  999),
]


def calc_hr_zone_distribution(hr_stream: list[float], lthr: float) -> list[dict]:
    """
    输入心率流（每秒采样），返回各区间累计秒数及占比。
    """
    if not hr_stream or not lthr:
        return []

    counts = [0] * len(HR_ZONES)
    for hr in hr_stream:
        if hr is None:
            continue
        ratio = hr / lthr
        for i, (_, lo, hi) in enumerate(HR_ZONES):
            if lo <= ratio < hi:
                counts[i] += 1
                break

    total = sum(counts)
    result = []
    for i, (name, _, _) in enumerate(HR_ZONES):
        secs = counts[i]
        result.append({
            "zone": name,
            "seconds": secs,
            "percent": round(secs / total * 100, 1) if total > 0 else 0,
        })
    return result


# ─────────────────────────────────────────
# 三项训练量平衡统计
# ─────────────────────────────────────────

SPORT_GROUPS = {
    "swim":  ["swim", "openwater"],
    "bike":  ["ride", "virtualride", "ebikeride"],
    "run":   ["run", "trailrun", "treadmill"],
}


def calc_triathlon_balance(activities: list, days: int = 28) -> dict:
    """
    统计最近 `days` 天三项各自的训练量（时长 / 距离 / 次数）。
    """
    cutoff = date.today() - timedelta(days=days)
    result = {
        "swim": {"count": 0, "duration_min": 0, "distance_km": 0},
        "bike": {"count": 0, "duration_min": 0, "distance_km": 0},
        "run":  {"count": 0, "duration_min": 0, "distance_km": 0},
    }

    for a in activities:
        if not a.start_date:
            continue
        act_date = a.start_date.date() if hasattr(a.start_date, "date") else a.start_date
        if act_date < cutoff:
            continue

        sport = (a.sport_type or "").lower()
        for group, sports in SPORT_GROUPS.items():
            if sport in sports:
                result[group]["count"] += 1
                result[group]["duration_min"] += round((a.moving_time or 0) / 60, 1)
                result[group]["distance_km"] += round((a.distance or 0) / 1000, 2)
                break

    return result
