# TriCoach API 参考

> 文档版本：v1.0（feat/users 分支）  
> Base URL: `http://localhost:8000`（生产环境见部署地址）

---

## 通用说明

### 认证

- 除 `/health`、`/auth/login`、`/auth/register`、`/strava/login`、`/strava/callback`、`/strava/status` 外，**大多数接口需要 Bearer Token**。
- 请求头：`Authorization: Bearer <jwt_token>`
- Token 有效期：默认 7 天

### 响应格式

- 成功：返回 JSON 对象，状态码 200
- 失败：返回 `{"detail": "错误信息"}`，常见状态码 400/401/403/404/500

---

## Auth 模块 (`/auth`)

### POST `/auth/register`
注册新账户。

**Body:**
```json
{
  "email": "user@example.com",
  "password": "secret123",
  "nickname": "Runner"   // 可选
}
```

**Response:**
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "user": { "id": 1, "email": "user@example.com", ... }
}
```

---

### POST `/auth/login`
邮箱密码登录。

**Body:**
```json
{
  "email": "user@example.com",
  "password": "secret123"
}
```

**Response:** 同 `/auth/register`

---

### GET `/auth/me`
获取当前用户信息。

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "id": 1,
  "email": "user@example.com",
  "nickname": "Runner",
  "firstname": null,
  "lastname": null,
  "profile_pic": null,
  "auth_provider": "password",
  "has_strava": false,
  "timezone": "Asia/Shanghai",
  "sleep_time": "22:00",
  "ftp": null,
  "lthr": null,
  "css": null,
  "run_threshold_pace": null
}
```

---

### PUT `/auth/profile`
更新个人资料。

**Body:**
```json
{
  "nickname": "NewName",
  "timezone": "Asia/Tokyo",
  "sleep_time": "23:00"
}
```

---

### POST `/auth/change-password`
修改密码。

**Body:**
```json
{
  "old_password": "secret123",
  "new_password": "newsecret456"
}
```

---

### POST `/auth/strava/disconnect`
解除 Strava 绑定。

> 安全限制：若当前账户未设置密码，返回 400，防止用户被锁在外面。

---

### GET `/auth/data-sources`
列出用户配置的其他数据源（如 Garmin）。

### POST `/auth/data-sources`
创建数据源。

**Body:**
```json
{
  "provider": "garmin",
  "client_id": "...",
  "client_secret": "..."
}
```

### DELETE `/auth/data-sources/{source_id}`
删除指定数据源。

---

### GET `/auth/state/{key}`
获取用户状态值（LLM 上下文等）。

**Response:**
```json
{ "key": "llm_context", "value": "...", "updated_at": "2026-04-01T..." }
```

### POST `/auth/state/{key}`
设置用户状态值。

**Body:** `{"value": "..."}`

### DELETE `/auth/state/{key}`
删除用户状态值。

---

## Strava 模块 (`/strava`)

### GET `/strava/login?state=<jwt>`
跳转到 Strava OAuth 授权页。
- `state` 可选：绑定模式时传入当前用户 JWT。

### GET `/strava/callback?code=...&state=...`
Strava 授权回调，内部处理登录/绑定逻辑，最后 302 跳回前端。

### GET `/strava/status`
检查当前认证状态（**无需登录也可访问**）。

**Response（已登录）:**
```json
{
  "authenticated": true,
  "user_id": 1,
  "name": "Runner",
  "profile_pic": null,
  "nickname": "Runner",
  "email": "user@example.com",
  "has_strava": true,
  "auth_provider": "both"
}
```

### GET `/strava/sync?since=YYYY-MM-DD`
触发后台同步用户 Strava 活动。

### GET `/strava/sync-logs?limit=20`
获取同步历史记录。

### GET `/strava/activities?limit=20`
获取当前用户最近活动列表。

**Response:**
```json
[
  {
    "id": 1,
    "strava_id": 123456789,
    "name": "Morning Run",
    "sport_type": "Run",
    "start_date": "2026-04-01T07:00:00",
    "distance": 10000,
    "moving_time": 3600,
    "avg_heart_rate": 150,
    "avg_power": null,
    "tss": 64.0,
    "is_excluded": false,
    "exclude_reason": null
  }
]
```

---

## Analysis 模块 (`/analysis`)

### GET `/analysis/calculate-tss`
为当前用户所有活动计算并保存 TSS。

**Response:**
```json
{
  "message": "TSS 计算完成",
  "updated": 10,
  "skipped_no_threshold": 2,
  "skipped_excluded": 1
}
```

### GET `/analysis/fitness?days=90`
返回 CTL / ATL / TSB 时序数据。

**Response:**
```json
[
  { "date": "2026-01-01", "ctl": 50.0, "atl": 60.0, "tsb": -10.0 },
  ...
]
```

### GET `/analysis/balance?days=28`
返回近 N 天游泳/骑行/跑步训练量分布。

**Response:**
```json
{
  "days": 28,
  "balance": {
    "swim": { "count": 2, "duration_min": 60.0, "distance_km": 2.0 },
    "bike": { "count": 5, "duration_min": 300.0, "distance_km": 150.0 },
    "run": { "count": 4, "duration_min": 240.0, "distance_km": 40.0 }
  }
}
```

### GET `/analysis/summary`
Dashboard 概览数据。

**Response:**
```json
{
  "fitness": { "ctl": 55.2, "atl": 62.0, "tsb": -6.8 },
  "balance_28d": { ... },
  "thresholds": { "ftp": 250, "lthr": 170, "css": 120, "run_threshold_pace": 300 },
  "total_activities": 42
}
```

### GET `/analysis/hr-zones/{activity_id}`
返回指定活动的心率区间分布。

### PUT `/analysis/thresholds`
更新用户训练阈值。

**Body:**
```json
{
  "ftp": 260,
  "lthr": 175,
  "css": 118,
  "run_threshold_pace": 295
}
```

---

## Anomalies 子模块 (`/analysis/anomalies`)

### GET `/analysis/anomalies`
扫描并返回当前用户的异常活动列表。

### GET `/analysis/anomalies/backfill`
补扫历史数据，自动排除异常并填充 `tss_adjusted=0`。

### POST `/analysis/anomalies/auto-exclude`
自动检测并排除所有异常活动。

### POST `/analysis/anomalies/{activity_id}/exclude?reason=...`
手动排除指定活动。

### POST `/analysis/anomalies/{activity_id}/include`
恢复被排除的活动。

---

## Coach 模块 (`/coach`)

### GET `/coach/open`
打开 Coach 页面，返回当前待处理或最近活跃的对话（含开场白）。

### POST `/coach/new`
开启新对话。

### POST `/coach/message/{conversation_id}`
发送用户消息，返回教练回复。

**Body:** `{"content": "昨天跑了10公里，感觉不错"}`

**Response:**
```json
{
  "reply": "很好！...",
  "is_complete": false,
  "model": "gemini-2.5-flash",
  "avatar_url": null
}
```

### GET `/coach/persona`
获取当前教练人设。

### PUT `/coach/persona`
更新教练人设。

**Body:** `{"name": "Coach Lily", "personality": "...", "style": "..."}`

### GET `/coach/conversations`
获取当前用户最近 20 条对话列表。

### GET `/coach/debug`
诊断 LLM 配置和连通性（开发调试用）。

---

## System

### GET `/health`
健康检查。

**Response:** `{"status": "ok", "version": "0.2.0"}`

### POST `/poll/trigger`
手动触发一次 Strava 轮询（测试用）。

### GET `/poll/status`
查看定时轮询任务状态。
