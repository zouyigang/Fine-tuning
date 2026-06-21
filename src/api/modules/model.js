import service from '@/api/request'

/**
 * 模型版本管理接口（已对接后端 FastAPI）。
 * 页面组件无需改动，函数签名与原 mock 版本保持一致。
 */

export function getModelList(params = {}) {
  return service.get('/model/list', { params })
}

export function updateModelStatus(id, status) {
  return service.put(`/model/${id}/status`, { status })
}

// 灰度发布监控
export function getGrayReleases() {
  return service.get('/model/gray-releases')
}

// 新建灰度发布（payload: { modelId, name, scope, traffic }）
export function createGrayRelease(payload) {
  return service.post('/model/gray-releases', payload)
}

// 扩大灰度流量
export function expandGrayTraffic(id, traffic) {
  return service.put(`/model/gray-releases/${id}/traffic`, { traffic })
}

// 全量上线（自动降级同类型原在线模型 + 写上线记录）
export function releaseModel(id, payload = {}) {
  return service.post(`/model/${id}/release`, payload)
}

// 快速回滚（目标模型置在线 + 写回滚审计记录）
export function rollbackModel(id, payload = {}) {
  return service.post(`/model/${id}/rollback`, payload)
}

// 候选模型：灰度待发布（已评估通过）/ 全量待上线（灰度中）
export function getGrayCandidates() {
  return service.get('/model/list', { params: { status: 'evaluated', pageSize: 100 } })
}

export function getReleaseCandidates() {
  return service.get('/model/list', { params: { status: 'gray', pageSize: 100 } })
}

export function getGrayTrend() {
  return service.get('/model/gray-trend')
}

// 上线/回滚记录
export function getReleaseHistory() {
  return service.get('/model/release-history')
}

// 可回滚的稳定版本
export function getRollbackCandidates() {
  return service.get('/model/rollback-candidates')
}

// 部署目标
export function getDeployTargets() {
  return service.get('/model/deploy-targets')
}

export const EXPORT_FORMATS = ['ONNX', 'TorchScript', 'PMML', 'SavedModel', 'GGUF']

// 归档列表
export function getArchiveList(params = {}) {
  return service.get('/model/archive', { params })
}
