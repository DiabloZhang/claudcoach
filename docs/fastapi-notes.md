# FastAPI 学习笔记

## /docs 页面是怎么来的

访问 `/docs` 时发生的事：

1. FastAPI 读取所有路由定义（路径、参数、HTTP 方法）
2. 自动生成一份 **OpenAPI 规范**（JSON 格式，可在 `/openapi.json` 查看）
3. FastAPI 内置了 **Swagger UI** 这个开源库
4. 浏览器访问 `/docs` → FastAPI 返回一个 HTML 页面 → HTML 加载 Swagger UI 的 JavaScript → JS 请求 `/openapi.json` → 渲染成交互文档

**结论**：这个页面我们一行前端代码都没写，FastAPI 自动生成。

## Chrome 和 Swagger UI 的关系

Chrome 不知道什么是 Swagger UI，它只是一个"JS 运行器"。
Swagger UI 是运行在 Chrome 里的 JavaScript 程序，负责把 API 定义渲染成可交互的界面。

## 为什么选 FastAPI

- 自动生成 `/docs` 交互文档，调试方便
- 性能好（基于 async/await）
- 代码简洁，类型提示完善

## API 方法：GET vs POST vs PUT

| 方法 | 用途 | 浏览器能直接访问？ |
|------|------|------------------|
| GET | 读取数据 | ✅ 可以 |
| POST | 创建/触发操作 | ❌ 需要用 /docs 或代码 |
| PUT | 更新数据 | ❌ 需要用 /docs 或代码 |

这也是为什么我们把 `calculate-tss` 和 `sync` 改成 GET——方便直接用浏览器触发。

## Railway 自动部署是怎么工作的

推代码后不需要手动在 Railway 点部署，因为 Railway 监听了 GitHub 仓库的 main 分支。

流程：
```
改代码 → git push → GitHub → Railway 检测到新 commit → 自动重新构建并部署
```

这个连接在建 Railway 项目时连接 GitHub 就自动开启了。

## 改文档算不算上线

不算。改 `docs/` 里的 `.md` 文件只是更新文档内容，虽然 Railway 会重新部署，但运行逻辑没有变化。真正影响运行的是 `backend/` 的 Python 代码和 `frontend/` 的 Next.js 代码。

## LTHR 是什么

LTHR = Lactate Threshold Heart Rate，乳酸阈值心率，单位 bpm。

训练中能长时间维持的最高心率，用来划分心率区间（Z1-Z5）。

粗估方法：最大心率 × 0.85～0.90
