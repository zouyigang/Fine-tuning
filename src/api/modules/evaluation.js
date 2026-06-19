import service from '@/api/request'

/**
 * 模型效果评估接口（已对接后端 FastAPI）。
 * 列表类读库；自动化指标/基准对比/场景验证为后端聚合分析结果。
 * 页面组件无需改动，函数签名与原 mock 版本保持一致。
 */

// 评估任务列表
export function getEvalList(params = {}) {
  return service.get('/evaluation/list', { params })
}

// 自动化指标（按模型类型）
export function getMetrics(modelType = 'ner') {
  return service.get('/evaluation/metrics', { params: { modelType } })
}

// 基准对比
export function getBenchmark() {
  return service.get('/evaluation/benchmark')
}

// 真实业务场景验证
export function getSceneValidation() {
  return service.get('/evaluation/scene-validation')
}

// 人工复核
export function getReviewSamples(params = {}) {
  return service.get('/evaluation/review-samples', { params })
}

export function getReviewSummary() {
  return service.get('/evaluation/review-summary')
}

// 错误案例分析
export function getErrorCases(params = {}) {
  return service.get('/evaluation/error-cases', { params })
}

// 评估报告
export function getReportList(params = {}) {
  return service.get('/evaluation/reports', { params })
}
