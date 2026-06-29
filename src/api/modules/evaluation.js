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

// 运行真实评估（payload: { modelId, datasetId, limit }）→ { evalTaskId, modelType }
export function runEvaluation(payload) {
  return service.post('/evaluation/run', payload)
}

// 轮询评估进度 / 结果
export function getEvaluationRun(evalTaskId) {
  return service.get(`/evaluation/run/${evalTaskId}`)
}

// 基准对比
export function getBenchmark() {
  return service.get('/evaluation/benchmark')
}

// 运行基准对比（微调模型 vs 基座模型，payload: { modelId, datasetId, limit }）
export function runBenchmark(payload) {
  return service.post('/evaluation/benchmark/run', payload)
}

// 轮询基准对比进度
export function getBenchmarkRun(evalTaskId) {
  return service.get(`/evaluation/benchmark/run/${evalTaskId}`)
}

// 真实业务场景验证
export function getSceneValidation() {
  return service.get('/evaluation/scene-validation')
}

// 运行场景验证（payload: { modelId, datasetIds, limit }）
export function runSceneValidation(payload) {
  return service.post('/evaluation/scene/run', payload)
}

// 轮询场景验证进度
export function getSceneRun(evalTaskId) {
  return service.get(`/evaluation/scene/run/${evalTaskId}`)
}

// 人工复核
export function getReviewSamples(params = {}) {
  return service.get('/evaluation/review-samples', { params })
}

export function getReviewSummary() {
  return service.get('/evaluation/review-summary')
}

// 复核抽样：真模型预测入复核队列（payload: { modelId, datasetId, count, reviewer }）
export function runReviewSampling(payload) {
  return service.post('/evaluation/review/sample', payload)
}

// 轮询复核抽样进度
export function getReviewRun(evalTaskId) {
  return service.get(`/evaluation/review/run/${evalTaskId}`)
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

// 删除评估报告
export function deleteReport(reportId) {
  return service.delete(`/evaluation/reports/${reportId}`)
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
