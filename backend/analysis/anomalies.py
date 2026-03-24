"""
训练数据异常检测
规则：按运动类型检查物理上不可能或极度异常的数据点
"""

from typing import Optional


# ─────────────────────────────────────────
# 检测规则（可调整阈值）
# ─────────────────────────────────────────

# 游泳：配速 < 55s/100m 视为不可能（世界纪录 ~44s/100m，业余最快约 55s）
SWIM_MIN_PACE_S_PER_100M = 55

# 骑行：平均时速 > 80km/h 视为异常（职业比赛平均也不超过 55km/h）
RIDE_MAX_AVG_SPEED_KMH = 80

# 跑步：配速 < 180s/km (3:00/km) 视为异常（世界纪录 ~167s/km，普通人不可能持续）
RUN_MIN_PACE_S_PER_KM = 180

# 单次活动 TSS > 400 视为可疑（铁人三项全程约 300-400，超过需注意）
SINGLE_TSS_THRESHOLD = 400

# 活动时长 > 18 小时视为异常
MAX_DURATION_SECONDS = 18 * 3600


def detect_anomalies(activity) -> list[str]:
    """
    检测单个活动的异常，返回问题描述列表（空列表 = 正常）。
    """
    reasons = []
    sport = (activity.sport_type or "").lower()
    duration = activity.moving_time or activity.elapsed_time or 0
    distance = activity.distance or 0

    # ── 通用检测 ──────────────────────────────

    # 时长异常
    if duration > MAX_DURATION_SECONDS:
        hours = duration / 3600
        reasons.append(f"时长异常：{hours:.1f}小时，超过18小时上限")

    # 距离为 0 但有时长（仅对有距离的运动检查，力量/瑜伽等不检查）
    GPS_SPORTS = ("swim", "openwater", "ride", "virtualride", "ebikeride", "run", "trailrun", "treadmill")
    if distance == 0 and duration > 600 and sport in GPS_SPORTS:
        reasons.append("距离为0但时长超过10分钟，疑似录制失败")

    # ── 游泳检测 ──────────────────────────────
    if sport in ("swim", "openwater"):
        if distance > 0 and duration > 0:
            pace_s_per_100m = (duration / distance) * 100
            if pace_s_per_100m < SWIM_MIN_PACE_S_PER_100M:
                reasons.append(
                    f"游泳配速异常：{pace_s_per_100m:.1f}s/100m，"
                    f"低于物理极限（世界纪录约44s/100m，阈值{SWIM_MIN_PACE_S_PER_100M}s）"
                )
        # 单次游泳超过 20km 也标记（极少数铁三中继赛除外）
        if distance > 20000:
            reasons.append(f"游泳距离异常：{distance/1000:.1f}km，超过20km")

    # ── 骑行检测 ──────────────────────────────
    elif sport in ("ride", "virtualride", "ebikeride"):
        if distance > 0 and duration > 0:
            avg_speed_kmh = (distance / duration) * 3.6
            if avg_speed_kmh > RIDE_MAX_AVG_SPEED_KMH:
                reasons.append(
                    f"骑行时速异常：{avg_speed_kmh:.1f}km/h，超过{RIDE_MAX_AVG_SPEED_KMH}km/h上限"
                )

    # ── 跑步检测 ──────────────────────────────
    elif sport in ("run", "trailrun", "treadmill"):
        if distance > 0 and duration > 0:
            pace_s_per_km = (duration / distance) * 1000
            if pace_s_per_km < RUN_MIN_PACE_S_PER_KM:
                mins, secs = divmod(int(pace_s_per_km), 60)
                reasons.append(
                    f"跑步配速异常：{mins}'{secs:02d}\"/km，"
                    f"低于阈值（3:00/km）"
                )

    # ── TSS 过高检测（已计算才检查）──────────────
    if activity.tss and activity.tss > SINGLE_TSS_THRESHOLD:
        reasons.append(
            f"TSS异常：单次{activity.tss:.0f}，超过{SINGLE_TSS_THRESHOLD}上限"
        )

    return reasons


def scan_all_anomalies(activities: list) -> list[dict]:
    """
    扫描全部活动，返回有异常的记录列表。
    """
    flagged = []
    for a in activities:
        reasons = detect_anomalies(a)
        if reasons:
            flagged.append({
                "id": a.id,
                "strava_id": a.strava_id,
                "name": a.name,
                "sport_type": a.sport_type,
                "start_date": a.start_date.isoformat() if a.start_date else None,
                "distance_km": round((a.distance or 0) / 1000, 2),
                "duration_min": round((a.moving_time or 0) / 60, 1),
                "tss": a.tss,
                "is_excluded": a.is_excluded,
                "exclude_reason": a.exclude_reason,
                "anomaly_reasons": reasons,
            })
    return flagged
