# TriCoach — AI-Powered Triathlon Training Assistant
> 规划文档，随对话持续更新
> 最后更新：2026-03-20

---

## 项目目标

1. **数据层**：从 Strava 获取原始训练数据（游泳 / 骑行 / 跑步）
2. **分析层**：专业铁三训练指标计算与可视化
3. **AI教练层**：基于训练数据的主动指导与计划制定
4. **开源友好**：任何人 clone 后能快速跑起来

---

## 技术选型

| 层次 | 技术 | 理由 |
|------|------|------|
| 后端 | Python + FastAPI | 数据分析生态最强 |
| 数据库 | SQLite（默认）/ PostgreSQL | 低门槛，无需额外安装 |
| 分析库 | pandas, numpy, fitparse | 训练数据处理 |
| 前端 | Next.js (JS) + Tailwind + Recharts | 生态丰富，开源社区接受度高 |
| AI | Claude API (claude-sonnet-4-6) | 推理能力强，适合教练角色 |
| 部署 | Docker Compose | 一命令起服务 |

---

## 项目结构

```
claudcoach/
├── backend/
│   ├── strava/       # OAuth + API 数据拉取 + Webhook
│   ├── analysis/     # 训练指标计算引擎
│   ├── ai_coach/     # AI教练逻辑（Claude API）
│   └── db/           # 数据模型
├── frontend/         # Next.js
├── docs/
├── docker-compose.yml
├── .env.example
├── PLAN.md
└── README.md
```

---

## 功能模块

### 模块一：Strava 数据接入
- OAuth2 授权流程（用户自己申请 Strava App）
- 历史数据批量同步
- Webhook 实时接收新活动
- 原始数据：GPS轨迹、心率流、功率流、步频、配速

### 模块二：训练分析引擎

| 指标 | 说明 |
|------|------|
| CTL / ATL / TSB | 慢性/急性训练负荷、体能状态指数 |
| TSS | 每次训练压力分 |
| FTP / LTHR / CSS | 功能阈值功率 / 心率 / 游泳速度 |
| 心率区间分布 | Z1-Z5 各区间时间占比 |
| 跑步经济性 | 步频、垂直振幅、触地时间 |
| 铁三专项 | 三项训练量平衡、砖课分析 |
| 功率曲线 | Power-Duration Curve（骑行）|

### 模块三：AI 铁三教练
- 上下文注入：最近训练数据 + 体能状态 + 目标赛事
- **主动点评**：新活动同步后自动生成训练反馈
- **计划制定**：根据目标赛事生成周训练计划
- **疲劳预警**：TSB 过低时主动推送警告
- **对话问答**：用户自由提问训练相关问题

### 模块四：开源体验
- 一键 Docker Compose 启动
- `.env.example` 覆盖所有配置项
- 详细的 Strava App 申请文档
- 支持自定义 LLM（可换 OpenAI 等）

---

## 部署与分发策略

### 运行模式三步走

**短期 — 本地 Self-hosted（MVP）**
- 在自己电脑上运行，浏览器访问 localhost
- Strava 新活动用**定时轮询**代替 Webhook（不依赖服务器在线）
- 用户 clone → 填 `.env` → `docker compose up` → 跑起来

**中期 — VPS 云端部署**
- 支持部署到云服务器（DigitalOcean / 阿里云等）
- Webhook 真正生效，24小时接收 Strava 推送
- 手机浏览器也能访问，响应式设计

**长期 — 视社区规模决定是否做 SaaS**
- 若用户量足够，考虑中心化服务
- 用户直接网页注册，无需自己部署

### 分享给其他用户（开源）
- 默认模式：每人自己跑一个实例
- 用户需要：Strava Developer App + Anthropic API Key
- 提供详细文档降低门槛

---

## 开发路线图

### Phase 1 — 本地 MVP（进行中，Step 5 待开始）

#### Step 1 — 后端骨架 `复杂度：低` ✅
- [x] FastAPI 项目初始化
- [x] 配置管理（读取 `.env`）
- [x] SQLite + SQLAlchemy 基础连接
- [x] 健康检查接口 `/health`

#### Step 2 — 数据模型 `复杂度：低` ✅
- [x] `User` 表：Strava token、FTP、LTHR、CSS 等阈值参数
- [x] `Activity` 表：strava_id、type、distance、duration、avg_hr、avg_power、start_date 等
- [x] `Stream` 表：原始时序数据（心率 / 功率 / 配速逐秒）

#### Step 3 — Strava OAuth `复杂度：中` ✅
- [x] **前置**：用户在 Strava 申请 Developer App，拿到 client_id + client_secret
- [x] 引导用户跳转 Strava 授权页（GET /auth/login）
- [x] 接收 callback，换取 access_token + refresh_token（GET /auth/callback）
- [x] Token 自动刷新逻辑（is_token_expired + refresh_access_token）

#### Step 4 — 历史数据同步 `复杂度：中` ✅
- [x] 调用 Strava API 拉取历史 activities 列表（分页）
- [x] 逐个拉取 streams（心率流、功率流、配速流）
- [x] 存入本地数据库
- [x] 断点续传（跳过已存在的 strava_id）
- [x] 后台异步执行，不阻塞请求（POST /auth/sync/{user_id}）

#### Step 5 — 训练指标计算 `复杂度：中高` ✅
- [x] TSS 计算（骑行用功率，跑步用配速/心率，游泳用配速）
- [x] CTL / ATL / TSB 计算（指数加权移动平均，CTL=42天，ATL=7天）
- [x] 心率区间分布（Z1-Z5，需用户设置 LTHR）
- [x] 三项训练量平衡统计（近28天次数/时长/距离）
- [x] 阈值设置接口（PUT /analysis/thresholds/{user_id}）
- [x] API 接口：/analysis/summary、/fitness、/balance、/hr-zones
- [x] 异常数据检测与排除（/analysis/anomalies，自动+手动两种方式）

**异常检测规则（已实现）**：
- 游泳配速 < 55s/100m（低于物理极限）
- 游泳单次 > 20km
- 骑行平均时速 > 80km/h
- 跑步配速 < 3:00/km（低于世界纪录级别）
- 单次 TSS > 400
- GPS运动（游泳/骑行/跑步）距离为0但时长 > 10分钟
- 排除后 TSS 置空，重新 calculate-tss 时自动跳过

**待办（Step 7/8 前端实现时补齐）**：
- [ ] 用户时区获取：从 Strava 返回的 timezone 字段读取，或首次使用时引导用户选择；当前已知用户时区为 Asia/Shanghai（UTC+8）；活动时间存储为 UTC，展示时需转换为本地时间
- [ ] 阈值初始化引导：首次使用时，引导用户自行输入已知阈值（FTP / LTHR / CSS / 跑步配速）
- [ ] 阈值估算兜底：若用户不知道，从历史数据估算（FTP=最大NP×0.95，LTHR=有氧均值×1.05，CSS=游泳均速×0.95，跑步阈值=跑步均速×0.9），加"~"标记提示仅供参考
- [ ] 异常检测规则用户自定义（两层）：
  - **基础层**：内置规则的阈值存入 User 表，设置页面可调（游泳最快配速、骑行最高时速、跑步最快配速、单次TSS上限）；提供"恢复默认值"
  - **扩展层（Prompt自定义规则）**：用户用自然语言描述额外规则（如"骑行 TSS > 300 标记"、"跑步距离 > 50km 警告"），存为文本；检测时将活动数据 + 用户自定义规则一起发给 Claude，由 AI 判断是否触发；返回触发原因供用户确认是否排除

**阈值初始化设计（待 Step 7/8 前端实现）**：
- 首次使用时，引导用户自行输入已知阈值（FTP / LTHR / CSS / 跑步配速）
- 若用户不知道，提供从历史数据估算的功能：
  - FTP 估算：最近90天最大标准化功率 × 0.95（或20分钟最大功率 × 0.95）
  - LTHR 估算：最近30天有氧训练平均心率 × 1.05
  - CSS 估算：最近30天游泳平均配速 × 0.95
  - 跑步阈值估算：最近30天跑步平均配速 × 0.9
- 估算值加 "~" 标记，提示用户仅供参考，建议通过实测校准

#### Step 6 — 定时轮询 `复杂度：低` ✅
- [x] 每小时自动拉取 Strava 最新活动（APScheduler，间隔可配置）
- [x] 新活动入库并触发指标计算
- [x] 替代 Webhook，本地无需公网地址

#### Step 7 — 前端骨架 `复杂度：低中` ✅
- [x] Next.js 初始化
- [x] 基础路由：Dashboard / Activities / Coach
- [x] 连接后端 API（lib/api.js）
- [x] 导航栏组件（Nav.js）

#### Step 8 — Dashboard 页面 `复杂度：中` ✅
- [x] CTL / ATL / TSB 折线图（体能状态趋势）
- [x] 最近活动列表（距离、时长、心率、TSS）
- [x] 三项训练量分布图（时长 + 距离双柱图）
- [x] 体能状态卡片（CTL / ATL / TSB 当前值）

---

### Phase 2 — 云端 + 分析深化

#### Phase 2a — Railway 云端部署 ✅（2026-03-26 完成）
- [x] SQLite → PostgreSQL 迁移（Railway 免费 PG）
- [x] 后端部署：https://claudcoach-production.up.railway.app
- [x] 前端部署：https://claudcoachfrontend-production.up.railway.app
- [x] Strava OAuth 云端授权，数据同步到 PG
- [x] Dashboard 增强：立即同步按钮、体能图高度切换（矮/中/高/超高）、悬浮显示当日训练

#### Phase 2b — 分析深化（待开始）
- [ ] Webhook 实时接收 Strava 推送（替代轮询）
- [ ] 心率 / 功率区间详细分析
- [ ] 训练日志详情页
- [ ] 功率曲线（Power-Duration Curve）
- [ ] 手机响应式适配

### Phase 3 — AI 教练

#### 3.1 教练人格与心情值
- [ ] 心情值（0-100）存数据库，持久化跨对话
- [ ] 四种状态与 emoji：
  - 🤩 亢奋（80-100）：充满热情，高度投入
  - 🙂 温和（60-79）：支持性，讲话温和
  - 🙃 冷静（40-59）：理性客观，话不多
  - 🤣🥵 冷淡（0-39）：对配合不好的学员耍脸色
- [ ] 心情均值 60，无刺激时自动向 60 回归
- [ ] 降低心情的行为：过度训练、连续多天不登录、忽视教练建议
- [ ] 提升心情的行为：按计划完成训练、主动汇报、达成目标
- [ ] 后续可扩展更多触发行为

#### 3.2 主动对话与记录
- [ ] 活动同步后自动触发训练点评
- [ ] 主动发起对话的时机：早起、睡前、训练前、训练后
- [ ] 每日总结（训练完后主动发起讨论生成）
- [ ] 周记（每周日主动发起）
- [ ] 月记（每月末主动发起）
- [ ] 赛记（赛事结束后发起）
- [ ] 赛季总结
- [ ] 所有记录存数据库，可回看

#### 3.3 训练计划
- [ ] 周训练计划生成
- [ ] 每日计划执行跟踪
- [ ] TSB 过低疲劳主动预警

#### 3.4 语音对话（Phase 3 之后实现）
- [ ] 实时流式语音对话（STT + TTS）
- [ ] 体验类似打电话

### Phase 4 — 语音 + 开源打磨
- [ ] 实时流式语音对话（STT + TTS）
- [ ] 完整 README + 使用文档
- [ ] 多语言支持（中 / 英）
- [ ] GitHub Actions CI
- [ ] （视情况）SaaS 模式

---

## 关键设计决策

| 决策 | 选择 | 原因 |
|------|------|------|
| 默认数据库 | SQLite | 零配置，个人用量足够 |
| AI主动触发 | Webhook → 分析 → Claude | 无需手动触发 |
| 数据存储 | 本地 | 保护用户隐私，无需云服务器 |
| Strava Token | 加密本地存储 | 安全 |
| 前端 | Next.js (JS) | 生态丰富，开源社区接受度高 |

---

## 临时需求（细节优化，不属于主线 Phase）

> 随时提出随时做，重新规划时再归类或清理

- [x] 体能趋势图高度可调（矮/中/高/超高切换）
- [x] Dashboard 立即同步按钮（触发 sync + calculate-tss + 刷新）
- [x] 体能趋势图悬浮显示当日训练明细（名称/时长/TSS）
- [x] 最近训练按天分组 + 每天气泡图（游泳→骑行→跑步，大小=TSS）
- [x] 异常活动显示「异常」标签，TSS 不计入统计
- [x] Activity 新增 `tss_adjusted` 字段（异常时=0，未来可修正为估算值）
- [x] 同步流程自动检测异常，新活动入库即时判断
- [x] `/backfill` 接口：历史数据一键补扫 + 标记异常
- [x] 立即同步按钮自动执行：sync → backfill → calculate-tss → 刷新
- [x] TSS/小时 > 100 显示「阈值偏低?」黄色标签（悬浮显示具体数值）
- [x] 两个同步按钮：立即同步（增量）+ 同步指定日期（手选起点）
- [x] SyncLog 表 + 同步记录 tab：展示每次同步时间/起点/新增/跳过/API调用/耗时/状态
- [ ] 2026-03-14 游泳数据标记排除（点同步按钮后自动处理）

---

## 待讨论 / 待决策

- [ ] 是否支持 Garmin / Wahoo 等其他数据源
- [ ] AI 教练的个性化程度（通用 vs 针对特定赛事距离）
- [ ] 是否需要用户账号系统（多用户 vs 单用户本地工具）

---

## 对话记录摘要

- 2026-03-20：初步规划，确定核心目标和技术方向
- 2026-03-20：前端确定用 Next.js (JS)，项目目录建立在 claudecode/claudcoach
- 2026-03-20：确定部署策略——短期本地轮询、中期VPS+Webhook、长期视情况SaaS
- 2026-03-20：细化 Phase 1 为 Step 1-8，逐步推进，当前在 Step 1 之前（准备阶段）
- 2026-03-20：Step 1-4 全部完成，数据库有 69 条 2026 年以来的真实训练数据，明天继续 Step 5
- 2026-03-23：Step 5 完成，TSS/CTL/ATL/TSB/三项平衡全部实现。用户阈值：FTP=260W，跑步配速=250s/km(4:10)，CSS=120s/100m(2:00)。当前体能：CTL=91.4，ATL=120.8，TSB=-29.4
- 2026-03-25：Phase 1 MVP 全部完成（Step 1-8）。讨论新想法并更新 Phase 3：教练心情值系统、主动对话机制、各类训练记录、语音对话（延后）、开发日记（docs/devlog/）
