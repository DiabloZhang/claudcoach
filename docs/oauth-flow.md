# Strava OAuth 授权流程

## 什么是 OAuth

OAuth 是一种授权协议，允许第三方应用（TriCoach）在不知道用户密码的情况下，获得访问用户数据的权限。用户始终在 Strava 官网上完成授权，我们只拿到一个"通行证"（token）。

## 完整流程图

```
你的浏览器                后端 (FastAPI)              Strava 服务器
     |                        |                            |
     | GET /auth/login        |                            |
     |----------------------->|                            |
     |                        | 307 跳转                   |
     |   strava.com/oauth?    |                            |
     |   client_id=214118&    |                            |
     |   redirect_uri=...     |                            |
     |<-----------------------|                            |
     |                                                     |
     | 浏览器自动跳到 Strava                                |
     |---------------------------------------------------->|
     |                                                     |
     |           Strava 显示"授权 TriCoach 访问你的数据"    |
     |                                                     |
     | 你点击授权                                           |
     |                                                     |
     |        Strava 带着 code 跳回我们的 callback          |
     | localhost:8000/auth/callback?code=abc123            |
     |<----------------------------------------------------|
     |                                                     |
     | GET /auth/callback?code=abc123                      |
     |----------------------->|                            |
     |                        | 用 code 换 token           |
     |                        |--------------------------->|
     |                        |   access_token             |
     |                        |<---------------------------|
     |                        |                            |
     |                        | 存入数据库 users 表         |
     |                        | 跳回前端 /?auth=success    |
     |<-----------------------|                            |
```

## 三个关键凭证

| 凭证 | 作用 | 有效期 |
|------|------|--------|
| `code` | 一次性临时授权码，Strava 回调时携带 | 只能用一次 |
| `access_token` | 真正用来调用 Strava API 拉数据的钥匙 | 6 小时 |
| `refresh_token` | 用来换新 access_token，无需重新授权 | 长期有效 |

## Token 自动刷新

access_token 6 小时后过期，但用户不需要重新授权。后端会自动检测：

```
每次调用 Strava API 之前：
  if 距离过期 < 60秒:
      用 refresh_token 换一个新的 access_token
      更新数据库
  继续正常请求
```

## 代码对应关系

| 流程步骤 | 代码位置 |
|----------|----------|
| 生成授权链接 | `strava/client.py` → `get_authorization_url()` |
| 跳转到 Strava | `strava/router.py` → `GET /auth/login` |
| 接收回调换 token | `strava/router.py` → `GET /auth/callback` |
| 检测并刷新 token | `strava/client.py` → `is_token_expired()` + `refresh_access_token()` |
| 保存到数据库 | `db/models.py` → `User` 表 |

## 为什么不直接用用户名密码

- 安全：我们永远不会接触到你的 Strava 密码
- 可撤销：你可以随时在 Strava 设置里取消 TriCoach 的授权
- 范围限制：我们只申请了 `activity:read_all` 权限，无法做其他操作
