# 模型微调通用平台 · 系统原型

基于业务功能清单实现的「模型微调通用平台」前端原型，面向公安业务场景，覆盖 **数据集管理、微调任务管理、模型效果评估、模型版本管理、微调配置管理** 五大模块共 30 个功能点。

## 技术栈

| 类别 | 选型 |
| --- | --- |
| 构建工具 | Vite 5 |
| 框架 | Vue 3 (`<script setup>`) |
| UI 组件库 | Element Plus（按需自动导入） |
| 路由 | Vue Router 4（hash 模式） |
| 状态管理 | Pinia |
| 图表 | ECharts 5 |
| HTTP | Axios（已封装拦截器，预留后端对接） |
| 样式 | SCSS |

## 🚀 一键启动（Docker，推荐）

> 从 git 把代码拉下来后，**无需在本机安装 MySQL / Node / Python**，一条命令即可起全套服务（MySQL + 后端 + 前端）。整个过程由 `docker-compose.yml` 编排，数据库自动建表、灌种子、创建默认账号。

### 0. 前置条件

- 安装并**启动** [Docker Desktop](https://www.docker.com/products/docker-desktop/)（Windows / macOS 都可）。
  - 验证：终端执行 `docker version`，能看到 `Server` 版本号即代表 Docker 守护进程已运行（只显示 Client 说明 Docker Desktop 没启动，先把它打开等托盘图标变绿）。
  - 验证 compose：`docker compose version` 能输出版本号。
- 占用端口：**5180**（前端）、**8000**（后端）、**3307**（MySQL，宿主侧）。确保这三个端口没被别的程序占用。
  - MySQL 容器宿主端口特意用 3307（容器内部仍是 3306），就是为了**避开本机已装的 MySQL（3306）**，两者可共存、互不影响。

### 1. 拉取代码

```bash
git clone <仓库地址> Fine-tuning
cd Fine-tuning
```

### 2.（可选）设置环境变量

不设置则用内置默认值，可直接跳到第 3 步。如需自定义，在**仓库根目录**新建 `.env`（该文件不会被提交）：

```dotenv
# MySQL root 密码（默认 root1234）
MYSQL_ROOT_PASSWORD=root1234
# 生产环境务必改成你自己的随机串
JWT_SECRET=please-change-me-in-prod
```

> 这些变量由 `docker compose` 注入容器，和本地 `server/.env` 互不干扰。

### 3. 构建并启动

在**仓库根目录**执行：

```bash
docker compose up -d --build
```

- 首次会拉取基础镜像（mysql:8.4 / python:3.11-slim / node:20-alpine / nginx:alpine）并构建前后端镜像，需几分钟，请耐心等待。
- `-d` 后台运行，`--build` 表示构建镜像（首次或改了代码后都要带）。
- 国内网络：构建已默认走国内镜像源（后端 pip 用清华源、前端 npm 用 npmmirror，写在各自 Dockerfile）。**境外**环境可把 Dockerfile 里对应的镜像源那行按注释删掉换回官方源。

### 4. 确认服务就绪

```bash
docker compose ps          # 三个容器都应是 Up；mysql 显示 (healthy)
docker compose logs -f backend   # 跟踪后端日志，看到 alembic 迁移完成 + Uvicorn 启动即 OK（Ctrl+C 退出日志查看，不影响容器）
```

启动编排是自动的：**mysql 健康检查通过 → 才启动 backend（容器内先跑 `alembic upgrade head` 建表，再 `AUTO_SEED` 灌种子）→ 再起 frontend（nginx）**。

健康检查：浏览器或 curl 访问 http://localhost:8000/api/health ，返回 `{"code":0,...,"status":"up"}` 即后端就绪。

### 5. 访问系统

- **前端入口**：http://localhost:5180
- **后端接口文档**：http://localhost:8000/docs
- 默认账号见下方[「访问地址与登录账号」](#访问地址与登录账号)（`admin / admin123`）。

### 常用运维命令

```bash
docker compose logs -f backend     # 看后端日志（frontend / mysql 同理）
docker compose restart backend     # 重启某个服务
docker compose up -d --build backend   # 只重建并重启后端（改了后端代码后）
docker compose up -d --build frontend  # 只重建并重启前端（改了前端代码后）
docker compose stop                # 停止全部容器（保留数据）
docker compose start               # 再次启动已停止的容器
docker compose down                # 停止并删除容器（数据卷保留，下次起来数据还在）
docker compose down -v             # ⚠️ 连数据库 / 上传文件数据卷一起删除（彻底重置，慎用）
```

### 数据持久化

- `mysql_data` 卷：数据库数据（库 `fine_tuning`）。
- `storage_data` 卷：数据集上传、模型导出、报告导出等文件（容器内 `/data/storage`）。
- `docker compose down` 不会删卷，数据保留；只有 `down -v` 才会清空。

### 常见问题排查

| 现象 | 原因 / 解决 |
| --- | --- |
| `docker version` 只显示 Client，没有 Server | Docker Desktop 没启动，打开它等托盘变绿再试 |
| 拉镜像报 `... : EOF` 或超时 | Docker Hub 网络瞬断，**重试** `docker compose up -d --build` 即可；或先手动 `docker pull mysql:8.4` 等逐个预拉再构建 |
| 端口被占用 `bind: address already in use` | 5180 / 8000 / 3307 被占用，先关掉占用进程，或改 `docker-compose.yml` 里 `ports` 的宿主端口 |
| backend 容器反复退出 | `docker compose logs backend` 看报错；多为连不上 mysql（等它 healthy）或环境变量问题 |
| 改了代码不生效 | 必须带 `--build` 重建镜像：`docker compose up -d --build backend`（或 `frontend`） |

---

## GPU 真实微调部署（可选）

> 默认 Docker 跑的是**模拟训练**（`ENGINE_MODE=sim`，造曲线演示，无需 GPU）。若要在本机用 **NVIDIA GPU** 跑**真实** LoRA/QLoRA 微调（LLaMA-Factory），用本节的 GPU 叠加配置。原理与版本锁定见 [`docs/真实微调引擎方案.md`](docs/真实微调引擎方案.md)。

### 0. 前置条件

- 一块 **NVIDIA GPU** + 安装**最新 N 卡驱动**（CUDA/cuDNN 由镜像内的 torch 自带，宿主**不用**装 CUDA Toolkit）。
- 让容器能用 GPU——按你的环境二选一：
  - **Windows / macOS（Docker Desktop）**：**无需**手动装 NVIDIA Container Toolkit，Docker Desktop 已内置 GPU 支持。只要：① 在 **Windows 主机**装最新 NVIDIA 驱动（**不是**在 WSL2 里装，WSL2 会自动获取）；② Docker Desktop 用 **WSL2 后端**（Settings → General 勾「Use the WSL 2 based engine」，默认即是）。
  - **Linux 原生 Docker**：才需手动装 `nvidia-container-toolkit`，然后 `sudo nvidia-ctk runtime configure --runtime=docker && sudo systemctl restart docker`。
  - 验证（两者通用）：`docker run --rm --gpus all nvidia/cuda:13.2.0-base-ubuntu22.04 nvidia-smi` 能列出你的显卡即 OK。
- 显存参考（单卡）：Qwen3-0.6B/1.7B/4B 可 LoRA/QLoRA；8B 建议 QLoRA(4bit)；14B+ 谨慎。

### 1. 放置离线基础模型

把 HF 格式权重放到宿主某目录，**子目录名 = 前端「基础模型」选项去掉「（开源）」后缀**。例如选 `Qwen3-0.6B（开源）` 就要有 `Qwen3-0.6B/`：

```
<你的模型目录>/
└── Qwen3-0.6B/
    ├── config.json
    ├── model.safetensors
    └── tokenizer.json ...
```

下载示例（ModelScope，国内快）：

```bash
pip install modelscope
python -c "from modelscope import snapshot_download; snapshot_download('Qwen/Qwen3-0.6B', local_dir='./models/Qwen3-0.6B')"
```

### 2. 启动（GPU 叠加配置）

在**仓库根目录**执行（把 GPU override 叠加在主 compose 上）。`MODELS_DIR` 指向上一步的模型根目录（不设则默认 `./models`）。**注意行内设环境变量的写法各 shell 不同**：

```powershell
# Windows PowerShell（先设变量，再启动；变量仅当前会话有效）
$env:MODELS_DIR = "d:/models"
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build
```

```bat
:: Windows cmd.exe（必须 set 单独一行，cmd 不支持 VAR=val 行内前缀）
set MODELS_DIR=d:/models
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build
```

```bash
# Linux / macOS（bash 支持行内前缀）
MODELS_DIR=./models docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build
```

- 它把 backend 换成 CUDA 镜像（`server/Dockerfile.cuda`：torch/torchaudio/torchvision 2.11.0+cu130 + LLaMA-Factory 0.9.5 + bitsandbytes≥0.49.2 以支持 QLoRA(4bit)）、置 `ENGINE_MODE=real`、`gpus: all`，并把宿主 `${MODELS_DIR}` 只读挂载到容器 `/data/models`。
- 首次构建会拉 torch（较大），耐心等。前端 / MySQL / 端口与默认一致。

### 3. 跑一次真实微调

前端「微调任务管理 → 任务创建」：选基础模型（如 `Qwen3-0.6B`）、数据集、微调方式（LoRA/QLoRA）、配超参 → 提交。任务进入 `pending` → 引擎按 GPU 并发拉起真实训练 → 「实时监控」看**真实 loss 下降与 GPU 利用率** → 训练完自动合并导出权重并生成「待评估」模型版本，接入评估/上线/部署闭环。

- 找不到所选数据集的上传文件时，会自动回退一个内置 demo 数据集，保证链路可跑通。
- 启停/重试：失败或中断的任务「断点重试」会从 checkpoint 续训；显存不足会给出 OOM 提示。

### 可配环境变量

| 变量 | 默认 | 说明 |
| --- | --- | --- |
| `MODELS_DIR` | `./models` | 宿主离线模型根目录（挂载到容器 `/data/models`） |
| `MAX_CONCURRENT_TRAINS` | `1` | 最大并发训练数（一般 = GPU 数） |
| `MYSQL_ROOT_PASSWORD` / `JWT_SECRET` | 同主 compose | 见上方一键启动节 |

### 切回模拟模式

不带 GPU override 即可（默认就是 sim）：`docker compose up -d --build`。

### 常见问题

| 现象 | 原因 / 解决 |
| --- | --- |
| `docker run --gpus all ...` 报 `could not select device driver` | 未装/未配置 NVIDIA Container Toolkit；按前置条件重装并重启 docker |
| 任务一直 `failed`，日志含 `out of memory` | 显存不足：改用 QLoRA、减小批次、缩短最大序列长度，或换更小模型 |
| 任务 `failed`，日志含「未在 MODELS_DIR 找到基础模型」 | 模型子目录名没对上（要等于选项去掉「（开源）」），或 `MODELS_DIR` 没指对 |
| 监控页 GPU 利用率为 0 | 容器内 `pynvml` 不可用或未透传 GPU；确认 `--gpus all` 生效（`docker compose ... exec backend nvidia-smi`） |

---

## 快速开始（本地开发联调，不用 Docker）

> 启动顺序：**① MySQL → ② 后端 → ③ 前端**。前端通过 vite 代理把 `/api` 转发到后端 `:8000`。

### ① 启动数据库（MySQL）

库 `fine_tuning`（root/1234）。Windows 服务名 `MySQL84`，默认手动启动：

```powershell
Start-Service MySQL84       # 若提示权限错误但服务已 Running 即可忽略
```

### ② 启动后端（FastAPI，端口 8000）

**首次先配置 `.env`**（仓库不含 `server/.env`，凭据不入库；用模板复制一份）：

```bash
cd server
cp .env.example .env        # Windows PowerShell：copy .env.example .env
```

- 默认 `.env` 用 **SQLite**（`finetune.db`，免装数据库、开箱即跑），适合快速试跑。
- 要用上一步的 **MySQL**：编辑 `server/.env`，把 `DATABASE_URL` 改成 MySQL 连接串（文件里已有注释示例）：
  ```dotenv
  DATABASE_URL=mysql+pymysql://root:你的密码@127.0.0.1:3306/fine_tuning?charset=utf8mb4
  ```
- 生产环境务必改 `JWT_SECRET`。
- 不建 `.env` 也能启动（走 SQLite 默认值），但就连不到你本地的 MySQL 了。

然后启动（Windows 建议用 anaconda 绝对路径，避免环境问题）：

```bash
D:/anaconda3/python.exe -m uvicorn app.main:app --port 8000
```

- 健康检查：http://localhost:8000/api/health
- 接口文档（Swagger）：http://localhost:8000/docs

### ③ 启动前端（Vite，端口 5180）

在项目根目录执行：

```bash
npm install      # 首次安装依赖
npm run dev      # 启动开发服务器，自动打开浏览器
npm run build    # 生产构建
npm run preview  # 预览构建产物
```

### 访问地址与登录账号

- **首页 URL**：http://localhost:5180/ （hash 路由，未登录自动跳 `#/login`，登录后进入 `#/dashboard/index`）
- **默认登录账号**（首次启动后端自动创建）：

  | 账号 | 密码 | 角色 |
  | --- | --- | --- |
  | admin | admin123 | 系统管理员 |
  | analyst | 123456 | 算法工程师 |
  | approver | 123456 | 审批管理员 |
  | labeler | 123456 | 标注人员 |

## 目录结构

```
src/
├── api/                 # 接口层（联调入口）
│   ├── request.js       # axios 实例 + 拦截器
│   └── modules/         # 按业务模块拆分的接口（已对接后端真实接口）
│       ├── dashboard.js
│       ├── dataset.js
│       ├── task.js
│       ├── evaluation.js
│       ├── model.js
│       └── config.js
├── components/          # 通用组件（BaseChart / StatCard / PageHeader）
├── layout/             # 整体布局（侧边栏 / 顶栏 / 多页签）
├── router/             # 路由即菜单配置（asyncRoutes）
├── store/              # Pinia（app / user）
├── styles/             # 全局样式与 SCSS 变量
├── utils/              # 工具（mock 模拟器 / 业务字典）
└── views/              # 页面，按模块分目录
    ├── dashboard/      # 工作台
    ├── dataset/        # 数据集管理（6）
    ├── task/           # 微调任务管理（6）
    ├── evaluation/     # 模型效果评估（6）
    ├── model/          # 模型版本管理（6）
    └── config/         # 微调配置管理（5）
```

## 模块与功能对照

| 一级 | 二级模块 | 三级功能 |
| --- | --- | --- |
| 模型微调 | 数据集管理 | 数据集导入 / 脱敏处理 / 多类型标注 / 版本管理 / 统计分析 / 权限控制 |
| 模型微调 | 微调任务管理 | 任务创建 / 超参可视化配置 / 实时监控 / 启停与重试 / 批量调度 / 训练日志 |
| 模型微调 | 模型效果评估 | 自动化指标 / 基准对比 / 场景验证 / 人工复核 / 错误案例分析 / 报告生成 |
| 模型微调 | 模型版本管理 | 版本列表 / 灰度上线 / 全量上线 / 快速回滚 / 导出部署 / 归档清理 |
| 模型微调 | 微调配置管理 | 基础模型库 / 超参模板 / 资源配置 / 自动调优 / 操作权限 |

## 后端对接说明

后端为 FastAPI 服务（见 `server/`，详见 `server/README.md`）。**前端所有接口模块均已从 mock 切换为真实后端**：

- `src/api/modules/*.js`（dashboard、dataset、task、evaluation、model、config、auth）全部改为 `service.get/post/put/delete(...)`，函数签名不变，页面组件零改动。
- `vite.config.js` 的 `server.proxy` 已把 `/api` 代理到 `http://localhost:8000`。
- `src/api/request.js` 统一处理 `{ code, data, message }` 响应结构与 token 注入；`code:401` 自动登出跳登录页。

进度：P0 脚手架 → P1 建表+种子 → P2 鉴权 → P3 数据集 → P4 任务+模拟训练 → P5 评估/版本/配置 → 工作台总览对接 → P6（操作日志审计、接口层 RBAC + 用户管理）→ 收尾批次（数据集真实上传、模型导出/部署/归档、报告 PDF/Excel 导出、批量调度持久化、Alembic 迁移、Docker 一键部署）→ 真实微调引擎 M1-M5（LLaMA-Factory 真实 LoRA/QLoRA、超参透传、真实指标/产物、控制面、断点续训/OOM、CUDA 镜像），均已完成。GPU 真实训练部署见上方「GPU 真实微调部署（可选）」。剩余：平台级 Token 刷新 / RBAC 收紧（与引擎解耦，可另排期）。
