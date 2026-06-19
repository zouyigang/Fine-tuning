import service from '@/api/request'

/**
 * 数据集管理接口（已对接后端 FastAPI）。
 * 页面组件无需改动，函数签名与原 mock 版本保持一致。
 * 其余模块仍走 mock，待后端逐模块上线后按此文件方式切换。
 */

export function getDatasetList(params = {}) {
  return service.get('/dataset/list', { params })
}

export function getDatasetDetail(id) {
  return service.get(`/dataset/${id}`)
}

export function createDataset(payload) {
  return service.post('/dataset', payload)
}

export function deleteDataset(id) {
  return service.delete(`/dataset/${id}`)
}

export function getDesensitizeRules() {
  return service.get('/dataset/desensitize-rules')
}

export function getAnnotationTasks(params = {}) {
  return service.get('/dataset/annotation-tasks', { params })
}

export function getDatasetVersions(datasetId) {
  return service.get('/dataset/versions', { params: { datasetId } })
}

export function getDatasetStatistics(datasetId) {
  return service.get('/dataset/statistics', { params: { datasetId } })
}

export function getDatasetPermissions(params = {}) {
  return service.get('/dataset/permissions', { params })
}
