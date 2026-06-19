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

## 快速开始（前后端联调）

> 启动顺序：**① MySQL → ② 后端 → ③ 前端**。前端通过 vite 代理把 `/api` 转发到后端 `:8000`。

### ① 启动数据库（MySQL）

库 `fine_tuning`（root/1234）。Windows 服务名 `MySQL84`，默认手动启动：

```powershell
Start-Service MySQL84       # 若提示权限错误但服务已 Running 即可忽略
```

### ② 启动后端（FastAPI，端口 8000）

在 `server/` 目录下执行（Windows 建议用 anaconda 绝对路径，避免环境问题）：

```bash
cd server
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

进度：P0 脚手架 → P1 建表+种子 → P2 鉴权 → P3 数据集 → P4 任务+模拟训练 → P5 评估/版本/配置 → 工作台总览对接，均已完成；P6（Alembic、操作日志、Docker）待办。
