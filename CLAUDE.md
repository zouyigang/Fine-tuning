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

## 当前状态

- 已是前后端动态系统：`src/api/modules/*` 全部对接真实接口，**无 mock 残留**；五大模块写操作均落库并自动审计。
- **真实微调引擎**（LLaMA-Factory）M1–M5 完成：单卡闭环 / 业务格式→alpaca 转换 / 控制面（启停重试·多卡并发）/ LoRA 合并导出 / GPU 采样·断点续训·OOM 处理 / CUDA 镜像。真跑 Qwen3-0.6B LoRA 验收 PASS。
- **数据流水线完整**：导入→标注→脱敏→发布→训练，含逐样本主干、真实脱敏、复核工作流、发布即落地、闭环门禁。
- **待办**：平台级 Token 刷新；RBAC 收紧（详见下「审计与 RBAC」）。逐批改动历史见 git log，方案文档在 `docs/`。

## 关键机制（改动前先了解）

- **引擎开关** `settings.ENGINE_MODE`：`sim`=模拟调度器（默认，零依赖）；`real`=`services/engine.py` 起子进程真实训练。宿主开发用 `real`。相关配置：`MODELS_DIR`(离线 HF 权重根)/`RUNS_DIR`/`MAX_CONCURRENT_TRAINS`。
- **数据集流水线状态机** `dataset.stage`：待标注→标注中→已标注→已脱敏→已发布→已归档（权威字段；`status` 旧字段仅兼容）。逐样本主干 `dataset_sample`(raw/labeled/masked/status，封顶 `SAMPLE_CAP=5000`)。复核通过才进「已标注」；**进入已标注及以后即锁定标注**（`save_sample_label` 后端拒改）。
- **业务格式 → alpaca `{instruction,input,output}`**：规则存 `convert_rule` 表，外键关联 `dataset_type`；维护页「配置管理 → 数据转换规则 / 数据集类型管理」。无库时回退 `services/dataset_convert.py:DEFAULT_RULES`。**发布即落地**——`publish_dataset` 把样本转成 alpaca 落 `dataset_file`，训练直读（引擎对 alpaca 直通、零转换）。
- **一标注多用途**：「实体关系标注」发布时按 `dataset_file.variant`(`ner`/`relation`) 产两份训练文件；引擎按任务 `modelType` 选文件（实体识别→ner / 关系抽取→relation，`dataset_file_for_task`）。其它类型单文件(`variant=None`)。
- **微调创建闭环门禁**（`routers/task.py`）：训练数据集必须 `stage=已发布`，且**数据集类型须与业务模型类型匹配**（`model_dataset_type_mismatch`）；解析不到的自由文本/演示放行，不破坏 sim。前端 `create.vue` 下拉已按模型类型过滤。
- **审计与 RBAC**：`core/oplog.py` 中间件自动记录所有写操作（读响应体 `code` 判成败，`_RULES` 映射语义，`_SKIP_PATHS` 排除只读 POST）——**新增写接口记得加 `_RULES`**。`deps.py:enforce_rbac` 按 `sys_role.granted` 拦 7 类高风险写操作（缺权限 `code:403`）；收紧需先补 `perm_catalog` 种子再加 `_RBAC_RULES`，否则非管理员会被全挡。
- **种子/迁移**：`AUTO_SEED=true` 且库空才灌演示数据；`ensure_*()`（用户 / 评估参考 / 数据集类型 / 转换规则 / 路径分析类型 / stage 回填）每次启动幂等执行，与演示数据解耦。Alembic 迁移 **inspector 幂等**，**须在 `server/` 目录**跑 `alembic upgrade head`。

## 验证套路

- 后端改完先冒烟：`python -c "from app.main import app"`。
- 逻辑/接口用 TestClient + 临时 SQLite（`ENGINE_MODE=sim`、`AUTO_SEED=false`、`DATABASE_URL=sqlite:///...`）跑端到端。
- 前端改完 `npm run build`。
- **坑**：`SessionLocal autoflush=False`——在同一事务里统计「刚改过状态的行」前需 `db.flush()`，否则查不到本次变更。
- 文件下载走 `src/utils/download.js`（独立 axios，注入 token、解析 RFC5987 中文名）；判错按 mime **精确等于** `application/json`（勿用子串，否则 `application/jsonl` 会被误判为错误）。

## 提交约定

- 仅在用户明确要求时才 commit / push。若需提交，注意 `server/.env` 等含凭据文件不应入库（确认 `.gitignore`）。
