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

// 本地上传数据集文件（multipart），返回 { fileId, fileName, size, sizeText, rows }
export function uploadDatasetFile(file) {
  const data = new FormData()
  data.append('file', file)
  return service.post('/dataset/upload', data, { headers: { 'Content-Type': 'multipart/form-data' } })
}

export function deleteDataset(id) {
  return service.delete(`/dataset/${id}`)
}

export function getDesensitizeRules() {
  return service.get('/dataset/desensitize-rules')
}

// 新增脱敏规则
export function createDesensitizeRule(payload) {
  return service.post('/dataset/desensitize-rules', payload)
}

// 启用/停用脱敏规则
export function toggleDesensitizeRule(id, enabled) {
  return service.put(`/dataset/desensitize-rules/${id}`, { enabled })
}

// 执行脱敏（标记目标数据集已脱敏）
export function runDesensitize(datasetId) {
  return service.post('/dataset/desensitize/run', { datasetId })
}

export function getAnnotationTasks(params = {}) {
  return service.get('/dataset/annotation-tasks', { params })
}

// 提交标注进度
export function updateAnnotationProgress(taskId, done) {
  return service.put(`/dataset/annotation-tasks/${taskId}/progress`, { done })
}

export function getDatasetVersions(datasetId) {
  return service.get('/dataset/versions', { params: { datasetId } })
}

// 数据集版本回滚（置为当前版本）
export function rollbackDatasetVersion(versionId) {
  return service.post(`/dataset/versions/${versionId}/rollback`)
}

export function getDatasetStatistics(datasetId) {
  return service.get('/dataset/statistics', { params: { datasetId } })
}

export function getDatasetPermissions(params = {}) {
  return service.get('/dataset/permissions', { params })
}

// 批量保存数据集权限（items: [{ id, roles, canView, canEdit, canExport }]）
export function saveDatasetPermissions(items = []) {
  return service.post('/dataset/permissions', { items })
}
