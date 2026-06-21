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

**已完成**

- P0 脚手架 / P1 建表+种子 / P2 鉴权(JWT) / P3 数据集 / P4 任务+模拟训练 / P5 评估·版本·配置 / 工作台总览对接 / P6-操作日志。
- 前端 `api/modules/*` **已全部对接真实接口（无 mock 残留）**。
- 已实现的写接口：`createTask`/`updateTaskStatus`、`createDataset`/`deleteDataset`、`updateModelStatus`、`saveBaseModel`、`saveHyperTemplate`/`deleteHyperTemplate`、`saveRolePermissions`、登录登出 + 操作日志自动记录。
- 操作日志：`core/oplog.py` 中间件自动记录所有写操作（GET 不记），登录在 `routers/auth.py` 内单独记（登录前无 token）；查询接口 `/log/list`、`/log/modules`；前端页「配置管理 → 操作日志审计」。表 `operation_log`。
- **「评估→上线→回滚」审批闭环（2026-06-21）**：灰度发布创建/扩流量（`POST /model/gray-releases`、`PUT /model/gray-releases/{id}/traffic`，关联模型置 `gray`）、全量上线（`POST /model/{id}/release`：目标置 `online`+同类型原在线降 `offline`+写 `release_history`，operator 取当前用户）、快速回滚（`POST /model/{id}/rollback`：同样降级+写 `release_history`）、评估报告生成（`POST /evaluation/reports`）、人工复核提交（`POST /evaluation/review-results` 批量更新 `review_sample`+重算准确率）。以上写操作均经中间件自动写审计；前端 `gray/release/rollback.vue`、`evaluation/report/review.vue` 已接真实接口（候选模型用 `model/list?status=` 过滤）。
- **数据集 + 配置写操作（2026-06-21）**：脱敏规则新增/启停（`POST/PUT /dataset/desensitize-rules`）、执行脱敏（`POST /dataset/desensitize/run` 置 `dataset.desensitized=True`）、版本回滚（`POST /dataset/versions/{id}/rollback` 切 `is_current`+同步主表版本号）、标注进度提交（`PUT /dataset/annotation-tasks/{id}/progress`，满 100% 转待审核）、权限批量保存（`POST /dataset/permissions`）、资源配额保存（`POST /config/resource-quotas` 按部门更新）、自动调优保存（`POST /config/autotune` 单行 upsert）。均经中间件自动写审计；前端 `desensitize/version/annotation/permission.vue`、`config/resource/autoTune.vue` 已接真实接口（目标数据集/候选用 `dataset/list`）。`VersionOut` 已补 `id` 字段。
- **接口层 RBAC + 用户管理（2026-06-21）**：`deps.py` 新增集中式 `enforce_rbac` 依赖（含 `_RBAC_RULES` 方法+路径正则→所需权限映射，仿 oplog `_RULES`），`main.py` 业务路由依赖由 `get_current_user` 换为 `enforce_rbac`。系统管理员放行全部；其余角色按 `sys_role.granted` 拦截高风险写操作（创建任务/配超参/审批上线/回滚/配额/权限分配），缺权限返回 `code:403`（HTTP 仍 200）。用户管理 CRUD：`/user/list`(GET)、`/user`(POST)、`/user/{id}`(PUT/DELETE)、`/user/{id}/reset-password`(POST)、`/user/{id}/status`(PUT)，写操作需「权限分配」；**禁止删除/禁用当前登录账号**防自锁。前端新增页「配置管理 → 用户与角色管理」(`config/userManage.vue`) + `api/modules/user.js`。**oplog 中间件升级**：改为读响应体 envelope `code` 判定成败（重建 response），RBAC 拒绝/业务失败如实记「失败」+原因，不再因 HTTP 200 误记「成功」。

**待办（按业务功能缺口梳理，2026-06-19）**

> 说明：以下「占位」= 前端有按钮但只弹 toast / setTimeout 假成功，未落库；「缺写接口」= 后端只有 GET 没有对应写接口。

1. 真实微调训练引擎（最大缺口，建议单独排期）
   - 现为模拟训练（`services/trainer.py` 造假指标）。缺：真实 pipeline（LLaMA-Factory/PEFT 等）、超参真正生效、GPU/资源调度、断点续训、训练完成自动生成 `model_version`、日志/指标来自真实进程。
2. 模型版本管理写操作（灰度/上线/回滚已完成 ✅，剩余）
   - 模型导出 / 部署到节点（`deploy.vue` 占位）、归档清理（`archive.vue` 占位）。
3. 模型效果评估写操作（报告生成、复核提交已完成 ✅，剩余）
   - 错误案例导出（`errors.vue` 占位）、报告 PDF/Excel 导出（`report.vue` 导出按钮仍占位）。
4. 数据集管理写操作（脱敏/标注/版本回滚/权限保存已完成 ✅，剩余）
   - 真实文件上传（导入仅写元数据，缺文件存储服务）、新建版本（仅有回滚）。
5. 微调任务管理补全
   - 批量调度移除/排序持久化（`schedule.vue`）、超参保存模板/应用到任务（`hyperparams.vue` 部分占位）、训练日志真实下载（`logs.vue`）。
6. 微调配置管理写操作（已完成 ✅）
   - 资源配额保存、自动调优保存/启动均已落库。
7. 系统/平台级（接口层 RBAC + 用户管理已完成 ✅，剩余）
   - 文件存储/下载服务、Token 刷新。RBAC 仅覆盖权限目录中的 7 类高风险写操作，其余写操作仍登录即可（权限目录无对应项）。
8. 工程收尾（原 P6 剩余）：Alembic 迁移、Docker compose 一键启动。

**优先级建议**：~~① 模型上线/回滚/灰度 + 评估报告/复核~~（✅）→ ~~② 数据集脱敏/标注/版本/权限 + 配额/调优保存~~（✅，剩真实文件上传）→ ~~③ 接口层 RBAC + 用户管理~~（✅）→ ④ 真实微调引擎（重，独立排期）。

## 提交约定

- 仅在用户明确要求时才 commit / push。若需提交，注意 `server/.env` 等含凭据文件不应入库（确认 `.gitignore`）。
