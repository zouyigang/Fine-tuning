import service from '@/api/request'

/**
 * 数据可视化大屏接口（已对接后端 FastAPI）。
 * 后端 /screen/overview 由各业务表实时聚合：核心指标 / 任务趋势 / 数据集分布 /
 * 标注进度 / 评估雷达 / GPU 负载 / 上线流水 / 操作流水 / 任务运行状态。
 * 页面组件 screen/index.vue 与 8s 轮询逻辑无需改动，函数签名与原 mock 版本一致。
 */
export function getScreenData() {
  return service.get('/screen/overview')
}
