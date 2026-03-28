"""
分析模块 API 路由
"""

from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db.database import get_db
from db.models import User, Activity, Stream
from analysis.metrics import (
    calc_tss_for_activity,
    calc_ctl_atl_tsb,
    calc_hr_zone_distribution,
    calc_triathlon_balance,
)
from analysis.anomalies import detect_anomalies, scan_all_anomalies

router = APIRouter(prefix="/analysis", tags=["analysis"])


# ─────────────────────────────────────────
# 计算并保存所有活动的 TSS
# ─────────────────────────────────────────

@router.get("/calculate-tss/{user_id}")
def calculate_tss(user_id: int, db: Session = Depends(get_db)):
    """
    为该用户所有活动计算 TSS 并写入数据库。
    需要用户先设置 ftp / lthr / css / run_threshold_pace。
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    activities = db.query(Activity).filter(Activity.user_id == user_id).all()

    updated = 0
    skipped = 0
    excluded = 0
    for a in activities:
        if a.is_excluded:
            excluded += 1
            continue
        tss = calc_tss_for_activity(a, user)
        if tss is not None:
            a.tss = tss
            updated += 1
        else:
            skipped += 1

    db.commit()
    return {
        "message": "TSS 计算完成",
        "updated": updated,
        "skipped_no_threshold": skipped,
        "skipped_excluded": excluded,
    }


# ─────────────────────────────────────────
# CTL / ATL / TSB 体能曲线
# ─────────────────────────────────────────

@router.get("/fitness/{user_id}")
def get_fitness(user_id: int, days: int = 90, db: Session = Depends(get_db)):
    """
    返回最近 N 天的 CTL / ATL / TSB 时序数据（用于前端折线图）。
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    activities = (
        db.query(Activity)
        .filter(Activity.user_id == user_id)
        .all()
    )

    # 按日期汇总当天有效 TSS（异常活动用 tss_adjusted，默认0）
    daily_tss: dict[date, float] = {}
    for a in activities:
        if not a.start_date:
            continue
        effective = a.tss_adjusted if a.is_excluded else a.tss
        if effective is None:
            continue
        d = a.start_date.date() if hasattr(a.start_date, "date") else a.start_date
        daily_tss[d] = daily_tss.get(d, 0.0) + effective

    result = calc_ctl_atl_tsb(daily_tss, end_date=date.today(), days=days)
    return result


# ─────────────────────────────────────────
# 心率区间分布（单次活动）
# ─────────────────────────────────────────

@router.get("/hr-zones/{user_id}/{activity_id}")
def get_hr_zones(user_id: int, activity_id: int, db: Session = Depends(get_db)):
    """
    返回指定活动的心率区间分布（需要用户已设置 LTHR）。
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if not user.lthr:
        raise HTTPException(status_code=400, detail="请先设置 LTHR（乳酸阈值心率）")

    activity = db.query(Activity).filter(
        Activity.id == activity_id, Activity.user_id == user_id
    ).first()
    if not activity:
        raise HTTPException(status_code=404, detail="活动不存在")

    stream = db.query(Stream).filter(Stream.activity_id == activity_id).first()
    hr_stream = (stream.heart_rate or []) if stream else []

    if not hr_stream:
        return {"zones": [], "message": "该活动无心率数据"}

    zones = calc_hr_zone_distribution(hr_stream, user.lthr)
    return {
        "activity_id": activity_id,
        "activity_name": activity.name,
        "lthr": user.lthr,
        "zones": zones,
    }


# ─────────────────────────────────────────
# 三项训练量平衡
# ─────────────────────────────────────────

@router.get("/balance/{user_id}")
def get_balance(user_id: int, days: int = 28, db: Session = Depends(get_db)):
    """
    统计最近 N 天游泳/骑行/跑步各自的训练量（次数/时长/距离）。
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    activities = (
        db.query(Activity)
        .filter(Activity.user_id == user_id)
        .all()
    )

    balance = calc_triathlon_balance(activities, days=days)
    return {"days": days, "balance": balance}


# ─────────────────────────────────────────
# 用户阈值设置（FTP / LTHR / CSS / 跑步配速）
# ─────────────────────────────────────────

@router.put("/thresholds/{user_id}")
def update_thresholds(
    user_id: int,
    ftp: float = None,
    lthr: float = None,
    css: float = None,
    run_threshold_pace: float = None,
    db: Session = Depends(get_db),
):
    """
    更新用户的训练阈值参数。
    - ftp: 功能阈值功率（瓦特，骑行用）
    - lthr: 乳酸阈值心率（bpm，骑行/跑步用）
    - css: 临界游泳速度（秒/100m）
    - run_threshold_pace: 跑步阈值配速（秒/km）
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if ftp is not None:
        user.ftp = ftp
    if lthr is not None:
        user.lthr = lthr
    if css is not None:
        user.css = css
    if run_threshold_pace is not None:
        user.run_threshold_pace = run_threshold_pace

    db.commit()
    return {
        "message": "阈值已更新",
        "ftp": user.ftp,
        "lthr": user.lthr,
        "css": user.css,
        "run_threshold_pace": user.run_threshold_pace,
    }


# ─────────────────────────────────────────
# 综合概览（Dashboard 用）
# ─────────────────────────────────────────

@router.get("/summary/{user_id}")
def get_summary(user_id: int, db: Session = Depends(get_db)):
    """
    返回当前体能状态快照：最新 CTL/ATL/TSB + 近28天三项平衡 + 近7天活动数。
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    activities = db.query(Activity).filter(Activity.user_id == user_id).all()

    # 体能状态（异常活动用 tss_adjusted，默认0）
    daily_tss: dict[date, float] = {}
    for a in activities:
        if not a.start_date:
            continue
        effective = a.tss_adjusted if a.is_excluded else a.tss
        if effective is None:
            continue
        d = a.start_date.date() if hasattr(a.start_date, "date") else a.start_date
        daily_tss[d] = daily_tss.get(d, 0.0) + effective

    fitness_series = calc_ctl_atl_tsb(daily_tss, end_date=date.today(), days=90)
    latest_fitness = fitness_series[-1] if fitness_series else {"ctl": 0, "atl": 0, "tsb": 0}

    # 三项平衡（近28天）
    balance = calc_triathlon_balance(activities, days=28)

    # 阈值状态
    thresholds = {
        "ftp": user.ftp,
        "lthr": user.lthr,
        "css": user.css,
        "run_threshold_pace": user.run_threshold_pace,
    }

    return {
        "fitness": latest_fitness,
        "balance_28d": balance,
        "thresholds": thresholds,
        "total_activities": len(activities),
    }


# ─────────────────────────────────────────
# 异常数据检测与管理
# ─────────────────────────────────────────

@router.get("/anomalies/{user_id}")
def get_anomalies(user_id: int, db: Session = Depends(get_db)):
    """
    扫描该用户所有活动，返回检测到的异常列表。
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    activities = db.query(Activity).filter(Activity.user_id == user_id).all()
    flagged = scan_all_anomalies(activities)

    return {
        "total_activities": len(activities),
        "anomaly_count": len(flagged),
        "anomalies": flagged,
    }


@router.post("/anomalies/{user_id}/{activity_id}/exclude")
def exclude_activity(user_id: int, activity_id: int, reason: str = "手动排除", db: Session = Depends(get_db)):
    """
    将指定活动标记为排除（不参与 TSS/CTL/ATL 计算）。
    """
    activity = db.query(Activity).filter(
        Activity.id == activity_id, Activity.user_id == user_id
    ).first()
    if not activity:
        raise HTTPException(status_code=404, detail="活动不存在")

    activity.is_excluded = True
    activity.exclude_reason = reason
    # 排除后清空 TSS，避免旧数据干扰
    activity.tss = None
    db.commit()

    return {"message": f"活动 {activity_id} 已排除", "reason": reason}


@router.post("/anomalies/{user_id}/{activity_id}/include")
def include_activity(user_id: int, activity_id: int, db: Session = Depends(get_db)):
    """
    恢复被排除的活动（重新加入计算）。
    """
    activity = db.query(Activity).filter(
        Activity.id == activity_id, Activity.user_id == user_id
    ).first()
    if not activity:
        raise HTTPException(status_code=404, detail="活动不存在")

    activity.is_excluded = False
    activity.exclude_reason = None
    db.commit()

    return {"message": f"活动 {activity_id} 已恢复，请重新运行 calculate-tss 更新数据"}


@router.get("/anomalies/{user_id}/backfill")
def backfill_anomalies(user_id: int, db: Session = Depends(get_db)):
    """
    补扫历史活动：检测异常并排除，已排除的补填 tss_adjusted=0。
    新部署后运行一次即可。
    """
    activities = db.query(Activity).filter(Activity.user_id == user_id).all()
    newly_excluded = []
    patched = 0

    for a in activities:
        # 已排除但 tss_adjusted 为空的，补填0
        if a.is_excluded and a.tss_adjusted is None:
            a.tss_adjusted = 0.0
            patched += 1
            continue
        # 未排除的，重新检测
        if not a.is_excluded:
            reasons = detect_anomalies(a)
            if reasons:
                a.is_excluded = True
                a.exclude_reason = "；".join(reasons)
                a.tss_adjusted = 0.0
                a.tss = None
                newly_excluded.append({"id": a.id, "name": a.name, "reasons": reasons})

    db.commit()
    return {
        "message": "历史数据补扫完成",
        "newly_excluded": len(newly_excluded),
        "patched_tss_adjusted": patched,
        "details": newly_excluded,
    }


@router.post("/anomalies/{user_id}/auto-exclude")
def auto_exclude_anomalies(user_id: int, db: Session = Depends(get_db)):
    """
    自动检测并排除所有异常活动（TSS 置空，等待重新计算）。
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    activities = db.query(Activity).filter(Activity.user_id == user_id).all()
    excluded = []

    for a in activities:
        if a.is_excluded:
            continue  # 已排除的跳过
        reasons = detect_anomalies(a)
        if reasons:
            a.is_excluded = True
            a.exclude_reason = "；".join(reasons)
            a.tss = None
            excluded.append({"id": a.id, "name": a.name, "reasons": reasons})

    db.commit()
    return {
        "message": f"自动排除完成，共排除 {len(excluded)} 条异常活动",
        "excluded": excluded,
    }
