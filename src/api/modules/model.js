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
