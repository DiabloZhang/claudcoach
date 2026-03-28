import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
from config import settings
from db.database import engine, Base, run_migrations
import db.models  # noqa: F401 — 注册所有模型，确保建表
from strava.router import router as strava_router
from analysis.router import router as analysis_router
from ai_coach.router import router as coach_router
from strava.poller import run_poll

logging.basicConfig(level=logging.INFO)

# 启动时自动建表 + 迁移新列
Base.metadata.create_all(bind=engine)
run_migrations()

scheduler = BackgroundScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动时开启调度器，关闭时停止"""
    scheduler.add_job(
        run_poll,
        trigger="interval",
        minutes=settings.poll_interval_minutes,
        id="strava_poll",
        replace_existing=True,
    )
    scheduler.start()
    logging.info(f"定时轮询已启动，间隔 {settings.poll_interval_minutes} 分钟")
    yield
    scheduler.shutdown()
    logging.info("定时轮询已停止")


app = FastAPI(title="TriCoach API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(strava_router)
app.include_router(analysis_router)
app.include_router(coach_router)


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.1.0"}


@app.post("/poll/trigger")
def trigger_poll():
    """手动触发一次轮询（测试用）"""
    scheduler.add_job(run_poll, id="manual_poll", replace_existing=True)
    return {"message": "轮询已触发，请稍后查看日志"}


@app.get("/poll/status")
def poll_status():
    """查看定时任务状态"""
    job = scheduler.get_job("strava_poll")
    if not job:
        return {"status": "not_running"}
    return {
        "status": "running",
        "interval_minutes": settings.poll_interval_minutes,
        "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
    }
