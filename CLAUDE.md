# CLAUDE.md — TriCoach 项目工作规范

本文件是给 Claude 的工作指导，每次开始新对话时自动加载。

---

## 工作哲学

### 能不依靠用户就不依靠用户

**核心原则**：遇到需要数据或操作的问题，优先做功能解决，而不是让用户手动查找或执行。

**反例**（错误做法）：
> 我不知道那条异常活动的 ID，请你打开 `/analysis/anomalies/1` 找一下 ID，然后告诉我。

**正例**（正确做法）：
> 我没有线上数据库访问权，但可以加一个 `/backfill` 接口，自动扫描所有异常、自动排除、自动补填字段。你只需要调用一次这个接口，之后不用再手动操作。

**判断标准**：每次要让用户"去找某个数据"或"手动执行某个步骤"时，先问自己：
- 能不能写一个接口自动完成？
- 能不能在同步/计算流程里顺带处理？
- 能不能用已有数据推断出来？

只有真正需要用户决策（比如：你想要A方案还是B方案？）才应该打断用户。

---

## 项目基本信息

- 项目路径：`/Users/bytedance/claudecode/claudcoach/`
- GitHub：`https://github.com/DiabloZhang/claudcoach`
- 后端：`https://claudcoach-production.up.railway.app`
- 前端：`https://claudcoachfrontend-production.up.railway.app`

## 用户信息

- 零编程经验，完全依赖 Claude 写代码
- 用中文沟通
- 喜欢边学边记，概念性问题记到 `docs/fastapi-notes.md`
- 偏好 step by step 推进，每步完成后更新 PLAN.md
- Chrome 有代理，本地用 127.0.0.1 而非 localhost

## 开发习惯

- 每次改完代码直接 commit + push，Railway 自动部署
- 临时需求记在 PLAN.md 的「临时需求」section
- 重要问题和学习笔记记在 `docs/fastapi-notes.md`
- 开发日志记在 `docs/devlog/YYYY-MM-DD.md`
