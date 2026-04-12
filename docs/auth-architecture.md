# TriCoach 认证与多用户架构设计

> 文档版本：v1.0（feat/users 分支）  
> 对应代码：`backend/auth/`, `backend/db/models.py`, `backend/strava/router.py`

---

## 1. 设计目标

- **支持多用户**：每个用户独立管理自己的训练数据、阈值设置、AI 教练对话。
- **双登录方式**：邮箱密码登录（本地账户）+ Strava OAuth 登录/绑定。
- **数据隔离**：所有业务查询必须基于 `current_user.id` 过滤，禁止跨用户访问。
- **向后兼容**：旧版单用户数据通过 migration 平滑升级，Strava Token 保留在 `User` 表。

---

## 2. 认证机制

### 2.1 JWT Bearer Token

- 用户注册/登录成功后，后端签发 JWT（HS256，默认 7 天有效期）。
- 前端将 token 存入 `localStorage`，每次请求通过 `Authorization: Bearer <token>` 携带。
- `auth.dependencies.get_current_user` 负责校验 token 并从数据库取出活跃用户。

```
┌─────────────┐      register/login        ┌─────────────┐
│   Frontend  │ ─────────────────────────> │  Auth API   │
│             │ <───────────────────────── │  (JWT)      │
└─────────────┘        access_token        └─────────────┘
       │
       │ 后续请求携带 Bearer Token
       ▼
┌─────────────┐
│  Protected  │
│    APIs     │
└─────────────┘
```

### 2.2 Strava OAuth 流程

支持两种模式：

1. **登录模式**：未登录用户点击「使用 Strava 登录」→ 授权回调 → 后端查找/创建用户 → 签发 JWT → 跳回首页。
2. **绑定模式**：已登录用户在 Settings 页点击「绑定 Strava」→ 将当前 JWT 作为 `state` 传给 Strava → 回调时解码 `state` 识别当前用户 → 把 Strava athlete_id/token 写入该用户。

> ⚠️ 安全注意：`state` 复用 JWT 会经过 Strava 服务器日志，存在泄露风险。后续应改为随机 nonce + 服务端映射。

---

## 3. 用户模型（核心字段）

```python
class User(Base):
    id: int                    # 内部主键，JWT 的 sub 字段
    email: str | None          # 唯一，可为空（Strava-only 用户）
    password_hash: str | None  # bcrypt，可为空
    nickname: str | None
    is_active: bool            # 软删除/禁用标记
    auth_provider: str         # password | strava | both

    # Strava OAuth（保留在 User 表保证兼容）
    strava_athlete_id: int | None   # 全局唯一，一个 Strava 账户只能绑一个 TriCoach 账户
    access_token: str | None
    refresh_token: str | None
    token_expires_at: int | None

    # 训练阈值（供 analysis 模块使用）
    ftp, lthr, css, run_threshold_pace: float | None

    # AI 教练偏好
    timezone: str
    sleep_time: str
```

### 关联模型

- `Activity`：每个活动归属一个用户。`strava_id` 与 `user_id` 组成**联合唯一约束**，避免不同用户同步同一 Strava 活动时冲突。
- `UserDataSource`：预留多数据源扩展（Garmin 等），Token 使用 Fernet 加密存储。
- `UserState`：存储 LLM 上下文、教练记忆等大文本 KV。
- `Conversation / Message`：AI 教练对话，按 `user_id` 隔离。

---

## 4. 数据隔离机制

所有业务路由统一使用 `current_user: User = Depends(get_current_user)`，并在数据库查询中显式过滤：

```python
# 示例：analysis/router.py
activities = db.query(Activity).filter(Activity.user_id == current_user.id).all()

# 示例：ai_coach/router.py
conv = db.query(Conversation).filter_by(user_id=current_user.id, status="pending").first()

# 示例：操作特定资源时做二次校验
if conv.user_id != current_user.id:
    raise HTTPException(403, "无权操作此对话")
```

### 关键修复历史

| 问题 | 影响 | 修复方式 |
|------|------|----------|
| `Activity.strava_id` 单独 `unique=True` | 多用户下同步同一 Strava 活动会冲突 | 改为 `UniqueConstraint("user_id", "strava_id")` |
| `sync.py` 的 `exists` 查询未过滤 `user_id` | 用户 A 同步过的活动，用户 B 无法同步 | 添加 `Activity.user_id == user.id` 条件 |
| `strava_disconnect` 未检查密码 | Strava-only 用户解绑后既无密码也无 Strava，无法登录 | 未设置密码时返回 400，拒绝解绑 |
| Strava 回调绑定冲突 | 一个 Strava 账户绑到第二个 TriCoach 账户时 500 | 绑定前检查是否已被其他用户绑定，返回友好错误页 |

---

## 5. 安全设计

### 5.1 密码与 Token 加密

- **密码**：`passlib[bcrypt]` 哈希存储，永远不存明文。
- **JWT**：`python-jose` HS256 签名，`secret_key` 控制安全性。
- **第三方 Token**：`Fernet` 对称加密（基于 `secret_key` 派生密钥），`UserDataSource` 中的 `access_token_encrypted` 等字段使用。

### 5.2 解绑安全

`auth/router.py` 中 `/auth/strava/disconnect` 强制要求：

```python
if not current_user.password_hash:
    raise HTTPException(400, "请先设置密码后再解除 Strava 绑定...")
```

这避免了 Strava-only 用户误操作后失去所有登录途径。

### 5.3 认证降级处理

前端 `api.js` 在收到 401 时自动清除 token 并跳转登录页：

```javascript
if (res.status === 401) {
    removeToken();
    window.location.href = '/login';
}
```

---

## 6. 扩展预留

- **角色权限**：当前所有用户均为普通用户，如需管理员后台，可在 `User` 表增加 `role` 字段。
- **OAuth 多样化**：`UserDataSource` 表已预留结构，后续可接入 Garmin、Coros 等。
- **Refresh Token 轮换**：当前 JWT 为固定 7 天有效期，后续可引入 refresh token 机制实现无感续期。
