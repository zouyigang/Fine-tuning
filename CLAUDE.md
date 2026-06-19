# CLAUDE.md

本文件为 Claude Code 在本仓库工作时的项目级指引，每次对话自动加载。请遵守其中约定。

## 项目概述

公安业务场景的「模型微调通用平台」。原为 Vue3 + Element Plus 静态原型，正逐模块改造为前后端动态系统：
- **前端**：Vue3 (`<script setup>`) + Element Plus + Vue Router(hash) + Pinia + ECharts + Vite，端口 5180。
- **后端**：FastAPI + SQLAlchemy 2.0 + APScheduler，端口 8000，位于 `server/`。
- **数据库**：本地 MySQL，库 `fine_tuning`，连接串见 `server/.env`（勿在本文件写明文密码）。
- 五大模块：数据集管理 / 微调任务管理 / 模型效果评估 / 模型版本管理 / 微调配置管理。

## 启动方式（顺序：① MySQL → ② 后端 → ③ 前端）

```bash
# ① 数据库：Windows 服务名 MySQL84（默认手动启动），未启会报 WinError 10061
Start-Service MySQL84

# ② 后端：必须在 server/ 目录，且用 anaconda 绝对路径（裸 python 易解析到错误解释器）
#    启动命令自带 UTF-8（chcp 65001 + PYTHONUTF8=1），避免控制台中文乱码
cd server
# PowerShell：
chcp 65001 > $null; $env:PYTHONUTF8 = "1"; D:/anaconda3/python.exe -m uvicorn app.main:app --port 8000
# Git Bash（mintty 终端本身即 UTF-8，只需设 Python）：
# PYTHONUTF8=1 /d/anaconda3/python.exe -m uvicorn app.main:app --port 8000

# ③ 前端：项目根目录
npm run dev
```

- 首页：http://localhost:5180/ （未登录跳 `#/login`，登录后进 `#/dashboard/index`）
- 后端健康检查 http://localhost:8000/api/health ，接口文档 http://localhost:8000/docs
- 默认登录账号：`admin / admin123`（另有 analyst、approver、labeler，密码 `123456`）

## 架构约定

- **后端分层**：`core/`(config·database·response·security) → `models/`(ORM) → `schemas/`(Pydantic) → `crud/`(读写) → `routers/`(路由) → `services/`(如模拟训练) → `deps.py`(依赖)。
- **统一响应**：`{code, data, message}`，成功 `code=0`；分页结构 `{list, total, page, pageSize}`。与前端 `src/api/request.js` 拦截器对齐，`code:401` 自动登出。
- **字段映射**：ORM 用 camelCase 属性映射 snake_case 列（如 `updatedAt = Column("updated_at", ...)`），让 Pydantic `from_attributes` 直接序列化成前端期望的 camelCase。
- **建表/种子**：启动时 `create_all` 自动建表；库为空时 `AUTO_SEED=true` 自动灌种子（`server/scripts/seed.py`）。默认账号由 `ensure_users()` 幂等创建。

## 工作模式（重要规则）

- **前端零侵入对接**：模块从 mock 切真实接口时，只改 `src/api/modules/*.js`（保持函数签名不变），**不改 `.vue` 页面**。
- **路由声明顺序**：具体路径（如 `/list`、`/versions`）必须声明在动态路由 `/{id}` 之前，避免被吞。
- **鉴权**：业务路由统一挂 `dependencies=[Depends(get_current_user)]`；`auth` 路由公开。
- **改动后验证**：后端改完先跑导入冒烟 `python -c "from app.main import app"`；接口验证用脚本登录拿 token 后调用；前端改完跑 `npm run build`。

## 环境坑（Windows 特有）

- **控制台是 GBK**：Python `print` 中文必然乱码，但**数据库与接口 JSON 是正确的 UTF-8**。排查中文别信终端显示——用「落盘到 UTF-8 文件 + Read 工具」核对。
- POST 含中文时避免在命令行内联 `-d`（Git Bash 会破坏 UTF-8），改用 `--data-binary @file` 或脚本发请求。

## 进度与待办

- 已完成：P0 脚手架 / P1 建表+种子 / P2 鉴权(JWT) / P3 数据集 / P4 任务+模拟训练 / P5 评估·版本·配置 / 工作台总览对接 / P6-操作日志。
- 前端 `api/modules/*` **已全部对接真实接口（无 mock 残留）**。
- 操作日志：`core/oplog.py` 中间件自动记录所有写操作（GET 不记），登录在 `routers/auth.py` 内单独记（登录前无 token）；查询接口 `/log/list`、`/log/modules`；前端页「配置管理 → 操作日志审计」。表 `operation_log`。
- 待办 P6 剩余：Alembic 迁移、Docker compose 一键启动。

## 提交约定

- 仅在用户明确要求时才 commit / push。若需提交，注意 `server/.env` 等含凭据文件不应入库（确认 `.gitignore`）。
