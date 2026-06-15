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

## 快速开始

```bash
npm install      # 安装依赖
npm run dev      # 启动开发服务器（默认 http://localhost:5180）
npm run build    # 生产构建
npm run preview  # 预览构建产物
```

## 目录结构

```
src/
├── api/                 # 接口层（联调入口）
│   ├── request.js       # axios 实例 + 拦截器
│   └── modules/         # 按业务模块拆分的接口（当前返回 mock 数据）
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

原型阶段所有数据由本地 mock 提供（见 `src/utils/mock.js` 与 `src/api/modules/*`），对接后端时：

1. 在 `src/api/modules/*.js` 中，将 `mockRequest(...)` 替换为 `service.get/post(...)`（每个函数下方已写好示例注释）。
2. 在 `vite.config.js` 的 `server.proxy` 中配置后端代理，或设置环境变量 `VITE_API_BASE`。
3. `src/api/request.js` 已统一处理 `{ code, data, message }` 响应结构与 token 注入，按后端实际约定微调即可。

页面组件不直接依赖 mock，仅调用 `api/modules` 暴露的方法，因此切换数据源对页面零侵入。
