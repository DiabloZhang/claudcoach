# CLAUDE.md — TriCoach 项目指南

本文件是给 AI 协作者的项目级工作指导，每次开始新对话时自动加载。

> AI 提示：如果你读到本文件，请先检查是否存在 `CLAUDE-<username>.md`（其中 `<username>` 为当前系统用户或对话发起者）。如果该文件存在，请同时读取并遵循其中的个人偏好。如果该文件不存在，请检查 Git 提交历史或项目文档中是否记录过该用户的个人工作习惯；如有记录，请生成对应的 `CLAUDE-<username>.md` 文件以供后续对话使用。本文件只保留项目共识，不包含任何特定协作者的个人习惯。

---

## 工作哲学

### 能不依靠用户就不依靠用户

**核心原则**：遇到需要数据或操作的问题，优先做功能/脚本解决，而不是让用户手动查找或执行。

**判断标准**：每次要让用户"去找某个数据"或"手动执行某个步骤"时，先问自己：
- 能不能写一个接口自动完成？
- 能不能在同步/计算流程里顺带处理？
- 能不能用已有数据推断出来？

只有真正需要用户决策（比如：你想要 A 方案还是 B 方案？）才应该打断用户。

---

## 项目信息

- GitHub: https://github.com/DiabloZhang/claudcoach
- 后端: https://claudcoach-production.up.railway.app
- 前端: https://claudcoachfrontend-production.up.railway.app
- 本地开发: `docker compose up`，访问 `http://localhost:3000`

---

## 技术栈

- 后端: Python + FastAPI + SQLAlchemy (SQLite / PostgreSQL)
- 前端: Next.js (JS) + Tailwind + Recharts
- AI: Claude API / Gemini
- 部署: Railway + Docker Compose

---

## 通用规范

- 不要直接 push 到 `main`。所有改动通过 feature branch → PR → merge。
- 修改数据库模型时，请同时考虑 PostgreSQL 和 SQLite 兼容性。
- 临时需求记在 `PLAN.md` 的「临时需求」section，开发日志写在 `docs/devlog/YYYY-MM-DD.md`。
