import service from '@/api/request'
import { downloadFile } from '@/utils/download'

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

// 删除模型版本（在线/灰度/核心模型后端会拒绝并提示）
export function deleteModel(id) {
  return service.delete(`/model/${id}`)
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

// 导出模型（生成产物并落库，payload: { format, quant }），返回导出记录含 id
export function exportModel(id, payload) {
  return service.post(`/model/${id}/export`, payload)
}

// 下载导出产物（浏览器另存为）
export function downloadExport(exportId) {
  return downloadFile(`/model/exports/${exportId}/download`)
}

// 模型版本关联的真实训练产物（adapter/merged 权重路径与大小）
export function getModelArtifacts(id) {
  return service.get(`/model/${id}/artifacts`)
}

// 部署模型到目标环境（payload: { targetId, format }），返回 { logs }
export function deployModel(id, payload) {
  return service.post(`/model/${id}/deploy`, payload)
}

// 归档列表
export function getArchiveList(params = {}) {
  return service.get('/model/archive', { params })
}

// 下载模型产物（归档/版本下载，浏览器另存为）
export function downloadModel(id, params = {}) {
  return downloadFile(`/model/${id}/download`, { params })
}

// 清理单个归档模型（核心模型会被拒绝）
export function cleanArchive(id) {
  return service.post(`/model/${id}/clean`)
}

// 批量清理归档模型
export function batchCleanArchive(ids = []) {
  return service.post('/model/archive/clean', { ids })
}

// 恢复归档模型（状态置为 offline）
export function restoreArchive(id) {
  return service.post(`/model/${id}/restore`)
}
