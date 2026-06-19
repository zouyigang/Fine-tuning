import service from '@/api/request'

/**
 * 工作台总览接口（已对接后端 FastAPI）。
 * 由后端从各业务表实时聚合：指标卡 / 任务趋势 / 模型类型分布 / 最近任务 / 待办。
 * 页面组件无需改动，函数签名与原 mock 版本保持一致。
 */

export function getDashboardOverview() {
  return service.get('/dashboard/overview')
}
