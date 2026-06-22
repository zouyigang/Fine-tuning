import service from '@/api/request'
import { downloadFile } from '@/utils/download'

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

// 生成评估报告（payload: { model, modelType, sections, format }）
export function generateReport(payload) {
  return service.post('/evaluation/reports', payload)
}

// 提交人工复核结果（results: [{ id, result }]）
export function submitReviewResults(results) {
  return service.post('/evaluation/review-results', { results })
}

// 导出评估报告（format: 'pdf' | 'excel'，浏览器另存为）
export function exportReport(reportId, format = 'pdf') {
  return downloadFile(`/evaluation/reports/${reportId}/export`, { params: { format } })
}

// 导出错误案例为 Excel（可按错误类型过滤）
export function exportErrorCases(errorType = '') {
  return downloadFile('/evaluation/error-cases/export', { params: { errorType } })
}
