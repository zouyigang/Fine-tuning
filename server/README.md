# 模型微调通用平台 · 后端服务

FastAPI + SQLAlchemy + MySAL/SQLite。前端 `src/api/modules/*` 按模块逐步对接本服务。

## 技术栈

| 类别 | 选型 |
| --- | --- |
| Web 框架 | FastAPI + Uvicorn |
| ORM | SQLAlchemy 2.0（迁移用 Alembic，P6 启用） |
| 校验 | Pydantic v2 + pydantic-settings |
| 数据库 | 默认 SQLite（开箱即跑），可切 MySQL |
| 鉴权 | JWT（python-jose）+ passlib（P2 启用） |
| 后台任务 | APScheduler（模拟训练，P4 启用） |

## 快速开始

当前 `.env` 已配置为本地 **MySQL（库 `fine_tuning`，root/1234）**，25 张表已建好并灌入种子数据。

```bash
cd server
pip install -r requirements.txt        # 安装依赖
python -m scripts.seed                  # 建表 + 灌种子（仅首次/重置时；启动也会自动建表）
uvicorn app.main:app --reload --port 8000
```

- 接口文档（Swagger）：http://localhost:8000/docs
- 健康检查：http://localhost:8000/api/health
- 启动时会自动建表；库为空时自动灌种子（`AUTO_SEED=true`）。

## 数据库

`.env` 的连接串：
```
DATABASE_URL=mysql+pymysql://root:1234@127.0.0.1:3306/fine_tuning?charset=utf8mb4
```
如需切回免安装的 SQLite（开发调试）：`DATABASE_URL=sqlite:///./finetune.db`，重启即可（ORM 模型 DB 无关）。

## 已建数据表（26 张）

| 模块 | 表 |
| --- | --- |
| 用户/权限 | sys_user、sys_role、perm_catalog |
| 数据集管理 | dataset、dataset_version、desensitize_rule、annotation_task、dataset_permission |
| 微调任务管理 | train_task、train_metric、train_log |
| 模型效果评估 | eval_task、eval_report、review_sample、error_case |
| 模型版本管理 | model_version、gray_release、release_history、deploy_target |
| 微调配置管理 | base_model、hyper_template、resource_quota、cluster_info、autotune_config、autotune_trial |
| 操作日志审计 | operation_log |

> `sys_user` 在 P2 鉴权落地后写入，`train_metric` 在 P4 模拟训练运行时写入，其余表均已灌入种子数据。

## 目录结构

```
server/
├─ app/
│  ├─ main.py            # 入口：中间件 / 路由 / 建表 / 异常封装
│  ├─ core/              # config / database / response（统一 {code,data,message}）
│  ├─ models/            # ORM 模型（已建：user + 数据集 5 张表）
│  ├─ schemas/           # Pydantic 出入参（字段与前端一致）
│  ├─ crud/              # 数据库读写
│  ├─ routers/           # 接口路由（已对接：dataset）
│  └─ deps.py            # 依赖注入
├─ scripts/seed.py       # 种子数据（迁移原前端 mock）
├─ requirements.txt
└─ .env / .env.example
```

## 已实现接口（数据集管理模块）

| 方法 | 路径 | 对应前端函数 |
| --- | --- | --- |
| GET | /api/dataset/list | getDatasetList |
| GET | /api/dataset/{id} | getDatasetDetail |
| POST | /api/dataset | createDataset |
| DELETE | /api/dataset/{id} | deleteDataset |
| GET | /api/dataset/desensitize-rules | getDesensitizeRules |
| GET | /api/dataset/annotation-tasks | getAnnotationTasks |
| GET | /api/dataset/versions | getDatasetVersions |
| GET | /api/dataset/statistics | getDatasetStatistics |
| GET | /api/dataset/permissions | getDatasetPermissions |

## 联调说明

- 前端 `vite.config.js` 已把 `/api` 代理到 `http://localhost:8000`。
- 统一响应结构 `{code:0,data,message}`，与前端 `src/api/request.js` 拦截器一致。
- 其余模块（任务/评估/版本/配置）仍走前端 mock，将按数据集模块的方式逐个迁移。

## 鉴权（P2 已完成）

- 登录 `POST /api/auth/login` → 返回 JWT + 用户信息；`GET /api/auth/me` 取当前用户；`POST /api/auth/logout`。
- 业务路由（dataset）已加 `Depends(get_current_user)` 保护；无/错 token 返回 `code:401`。
- 前端：登录页 + 路由守卫（未登录跳 `/login`）+ `request.js` 自动注入 token，401 自动登出。
- 密码 pbkdf2_sha256 哈希存储。默认账号（首启动自动创建）：

  | 账号 | 密码 | 角色 |
  | --- | --- | --- |
  | admin | admin123 | 系统管理员 |
  | analyst | 123456 | 算法工程师 |
  | approver | 123456 | 审批管理员 |
  | labeler | 123456 | 标注人员 |

## 模拟训练（P4 已完成）

- `app/services/trainer.py`：APScheduler 每 3 秒推进所有 `running` 任务，写 `train_metric` + `train_log`，进度满 100% 自动 `success`。
- 演示任务（id=1）常驻运行、进度封顶 99%、永不结束，保证「实时监控」页随时有滚动曲线。
- 任务接口：`/task/list`、`/task`(创建)、`/task/{id}/status`、`/task/running`、`/task/curve`、`/task/resource-usage`、`/task/logs`、`/task/schedule`。
- 前端 6 个任务页面已切到真实接口；监控页 2 秒轮询读取后端实时指标。

## 评估 / 版本 / 配置（P5 已完成）

三个模块的 schemas/crud/routers 已落地并接入鉴权，前端 `src/api/modules/{evaluation,model,config}.js` 已全部从 mock 切到真实接口。

| 模块 | 主要接口 |
| --- | --- |
| 模型效果评估 | `/evaluation/list`、`/evaluation/metrics`、`/evaluation/benchmark`、`/evaluation/scene-validation`、`/evaluation/review-samples`、`/evaluation/review-summary`、`/evaluation/error-cases`、`/evaluation/reports` |
| 模型版本管理 | `/model/list`、`/model/{id}/status`、`/model/gray-releases`、`/model/gray-trend`、`/model/release-history`、`/model/rollback-candidates`、`/model/deploy-targets`、`/model/archive` |
| 微调配置管理 | `/config/base-models`(GET/POST)、`/config/hyper-templates`(GET/POST/DELETE)、`/config/resource-quotas`、`/config/autotune`、`/config/role-permissions`(GET/POST) |

- 列表/明细类读库；自动化指标、基准对比、场景验证为后端聚合分析结果（不单独建表）。
- 复核汇总（review-summary）、错误类型分布（error-cases.dist）由库内数据实时聚合。
- 权限矩阵保存：前端 `{角色:{权限:bool}}` 矩阵在 `config.js` 转为 `{roles:[{role,granted}]}` 落库。

> Windows 下启动建议用 anaconda 绝对路径，避免环境/PATH 问题：
> ```
> D:/anaconda3/python.exe -m uvicorn app.main:app --port 8000
> ```

## 操作日志审计（P6 已完成其一）

- `app/core/oplog.py`：HTTP 中间件自动记录所有写操作（POST/PUT/DELETE），GET 只读不记；按路径映射成「模块 + 操作」语义，从 Bearer token 解析操作人，记录 IP/结果/时间，写入 `operation_log`。
- 登录在 `routers/auth.py` 内单独记录（登录前无 token），含成功/失败与原因。
- 查询接口：`GET /log/list`（按账号/模块/结果/关键字筛选 + 分页）、`GET /log/modules`（筛选项）。
- 前端页面：「配置管理 → 操作日志审计」（`src/views/config/operationLog.vue`）。

## 后续阶段

- **P2** 鉴权：登录接口 + JWT + 前端登录页/路由守卫 ✅
- **P4** 任务模块 + 模拟训练 ✅
- **P5** 评估 / 版本 / 配置 三模块接口迁移 ✅
- **P6** 操作日志审计 ✅ ；待办：Alembic 迁移、Docker compose 一键启动
