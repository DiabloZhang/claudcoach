# TriCoach 🏊🚴🏃

AI-Powered Triathlon Training Assistant — connects to Strava, analyzes your training data, and gives you a proactive AI coach.

## Features

- **Strava Integration**: Sync all your swim, bike, run activities
- **Training Analytics**: CTL/ATL/TSB, TSS, power curves, HR zones
- **AI Coach**: Auto-commentary on every workout, weekly plan generation, fatigue alerts
- **Self-hosted**: Your data stays local

## Quick Start

```bash
# 1. Clone
git clone https://github.com/yourname/claudcoach.git
cd claudcoach

# 2. Configure
cp .env.example .env
# Edit .env with your Strava App credentials and Anthropic API key

# 3. Run
docker compose up
```

Open http://localhost:3000

## Setup Guide

### 1. 申请 Strava API App

> Strava 菜单里没有直接入口，需要手动访问：**strava.com/settings/api**

填写以下内容：
- **Application Name**：随意，如 `TriCoach`
- **Website**：`http://localhost`
- **Authorization Callback Domain**：`localhost`

提交后拿到 `Client ID` 和 `Client Secret`，填入 `.env`。

### 2. 申请 Anthropic API Key

前往 console.anthropic.com 注册并创建 API Key，填入 `.env`。

## Tech Stack

- **Backend**: Python + FastAPI
- **Frontend**: Next.js
- **Database**: SQLite (default)
- **AI**: Claude API

## License

MIT
