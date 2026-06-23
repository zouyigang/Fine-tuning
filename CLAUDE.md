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

## Docker 一键启动（可替代上面的本地三步）

`docker-compose.yml` 在仓库根目录，编排 mysql + backend + frontend 三个服务，**无需本地装 MySQL/Node/Python**。

```bash
# 在仓库根目录执行（需已装 Docker Desktop 并启动）
docker compose up -d --build      # 首次或代码变更后：构建并后台启动
docker compose logs -f backend    # 跟踪后端日志（含 alembic 迁移 + 启动）
docker compose ps                 # 查看三个容器状态
docker compose down               # 停止并移除容器（数据卷保留）
docker compose down -v            # 连同 mysql/storage 数据卷一起清除（慎用）
```

- 访问入口同本地：前端 http://localhost:5180 、后端文档 http://localhost:8000/docs 、默认账号 `admin / admin123`。
- 启动顺序自动编排：mysql healthcheck 通过后才起 backend；**backend 容器启动前先跑 `alembic upgrade head` 建表**（既有库自动补建缺表），再 `AUTO_SEED` 灌种子。
- 数据持久化在命名卷：`mysql_data`(数据库)、`storage_data`(上传/导出文件，容器内 `/data/storage`)。
- **端口**：MySQL 宿主映射 **3307**(容器内仍 3306)，避开本地常驻 MySQL84(3306)；前端 5180、后端 8000 同本地。
- **构建依赖国内镜像**（CN 网络更稳）：后端 `pip` 走清华源、前端 `npm` 走 npmmirror（写在各自 Dockerfile，境外可按注释删掉换回官方源）。基础镜像若 `docker compose up` 拉取报 EOF，多为 Docker Hub 瞬断，重试或先 `docker pull` 预拉即可。
- 镜像已含运行所需全部依赖（含 `pytz`，APScheduler 调度 + `trainer.py` 直接 import）。
- 可配环境变量（`docker compose` 读 shell 环境或根目录 `.env`，**不提交**）：`MYSQL_ROOT_PASSWORD`(默认 `root1234`)、`JWT_SECRET`(默认占位，生产必须改)。容器内连接串由 compose 注入 `mysql` 服务名，与本地 `server/.env` 互不影响。
- nginx(`nginx.conf`) 把前端 `/api/` 反代到 `backend:8000`，并放宽上传体积到 512MB（数据集最大 500MB）。
- 仅改前端代码需重建 frontend 镜像：`docker compose up -d --build frontend`；仅改后端同理 `--build backend`。

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

- **收尾批次（2026-06-22）**：以下占位/缺口全部落地，新增 `core/storage.py` 本地文件存储服务（`server/storage/` 下 datasets/models/reports 三子目录，已 gitignore）+ 前端 `src/utils/download.js` 二进制下载工具（独立 axios，注入 token、解析 RFC5987 中文文件名、识别 JSON 错误）。
  - **数据集真实上传**：`POST /dataset/upload`（multipart）落盘 + 估算样本量（json 解析/其余按非空行），写 `dataset_file` 表；`createDataset` 支持 `fileId` 关联回填 dataset_id 并以真实行数为 total。前端 `import.vue` 接真实上传。
  - **模型导出/部署/归档**：导出 `POST /model/{id}/export` 生成产物 manifest 落盘 + 写 `model_export` 表，`GET /model/exports/{id}/download` 下载；部署 `POST /model/{id}/deploy` 写 `model_deployment` 表 + 抬高目标负载并回传日志；归档清理 `POST /model/{id}/clean`（核心模型 F1>0.93 拒绝，否则删行）、批量 `POST /model/archive/clean`、恢复 `POST /model/{id}/restore`、下载 `GET /model/{id}/download`。前端 `deploy.vue`/`archive.vue` 接真实接口。
  - **报告/错误案例导出**：`services/reporting.py`（reportlab 内置 CJK 字体 STSong-Light 生成 PDF、openpyxl 生成 xlsx）。`GET /evaluation/reports/{id}/export?format=pdf|excel`、`GET /evaluation/error-cases/export?errorType=`，落盘 storage/reports 后下载。前端 `report.vue` 两个导出按钮、`errors.vue` 导出接真实接口。
  - **批量调度持久化**：新增 `schedule_item` 表（与 train_task 解耦，含 seq/优先级/计划时间），首次访问以当前 pending/running 任务播种。`GET /task/schedule` 读持久化队列、`POST /task/schedule` 新建、`PUT /task/schedule/reorder` 重排、`DELETE /task/schedule/{id}` 移除。前端 `schedule.vue` 上移/下移/移除/新建均落库。
  - **工程收尾**：Alembic（`server/alembic.ini` ASCII-only 避免 GBK 读取报错 + `migrations/env.py` 从 settings 读 URL、target=Base.metadata 支持 autogenerate + `0001_baseline` 以 metadata.create_all(checkfirst) 为基线）；Docker（`server/Dockerfile` 启动前 `alembic upgrade head`、`Dockerfile.web` 多阶段 + `nginx.conf` 反代 /api、`docker-compose.yml` mysql+backend+frontend 一键起）。`requirements.txt` 增 reportlab/openpyxl。
  - 以上写操作均经 oplog 中间件自动审计（已加 `_RULES`：上传/导出/部署/清理/恢复/调度增删排序），冒烟验证全部记「成功/失败」准确。

- **收尾小项批次（2026-06-23）**：清掉 4 个占位/缺口，TestClient + 临时 SQLite 端到端冒烟 10/10 通过。
  - **训练日志真实下载**：`GET /task/{id}/logs/download?level=&keyword=` 拼装 `.log` 纯文本（`text/plain; charset=utf-8` + `Content-Disposition: train-task-{id}.log`），前端 `logs.vue` 下载按钮经 `downloadFile` 真实下载（支持当前级别/关键字过滤）。GET 不入审计。
  - **超参保存为模板**：`hyperparams.vue` 「保存为模板」由 toast 改为 `ElMessageBox.prompt` 取名后调已存在的 `saveHyperTemplate`（`POST /config/hyper-templates`，受 RBAC「配置超参数」约束），落 `hyper_template` 表。
  - **数据集新建版本**：`POST /dataset/versions`（`crud.create_version`：`_next_version` 顺延 vX.Y → 次版本+1 / 置当前 / 同步主表版本号与样本量；author 取当前用户）；schema `VersionCreateIn`；前端 `version.vue` 加「新建版本」按钮+弹窗。oplog 加规则「新建数据集版本」。
  - **上传 schema/格式校验**：`storage.validate_dataset` 按后缀校验（json 须为非空数组或含数组的对象 / jsonl 每行须合法 JSON / csv 须表头+≥1 行 / txt 须≥1 非空行），不合格删除已落盘文件并 `code:4001` 返回原因；`/dataset/upload` 以校验后行数为样本量。
  - **未做（随引擎做，见待办）**：超参「应用到任务」（需把超参挂到训练运行，由 LLaMA-Factory 引擎定义，`TrainTask` 现无超参列）。

**待办（更新于 2026-06-23）**

> 说明：以下「占位」= 前端有按钮但只弹 toast / setTimeout 假成功，未落库；「缺写接口」= 后端只有 GET 没有对应写接口。

1. 真实微调训练引擎（最大缺口，**下一步**，已定方向：本机 NVIDIA GPU + LLaMA-Factory）
   - 现为模拟训练（`services/trainer.py` 造假指标）。缺：真实 pipeline（LLaMA-Factory）、超参真正生效（含「超参模板/配置应用到任务」落地）、GPU/资源调度、断点续训、训练完成自动生成 `model_version`、日志/指标来自真实进程。
2. 系统/平台级（与引擎解耦，可单独排期）：Token 刷新；RBAC 仅覆盖权限目录中的 7 类高风险写操作，新增的导出/部署/清理等写操作仍登录即可（权限目录无对应项，收紧需先补 `perm_catalog` 种子再加 `_RBAC_RULES`，否则非管理员会被全挡）。

**优先级建议**：~~① 上线/回滚/灰度 + 评估闭环~~（✅）→ ~~② 数据集脱敏/标注/版本/权限 + 配额/调优~~（✅）→ ~~③ 接口层 RBAC + 用户管理~~（✅）→ ~~收尾项（文件上传/导出/部署/归档/调度持久化/Alembic/Docker）~~（✅，2026-06-22）→ ~~收尾小项（日志下载/超参存模板/新建版本/上传校验）~~（✅，2026-06-23）→ ④ 真实微调引擎（本机 GPU + LLaMA-Factory，重，下一步）。

## 提交约定

- 仅在用户明确要求时才 commit / push。若需提交，注意 `server/.env` 等含凭据文件不应入库（确认 `.gitignore`）。
