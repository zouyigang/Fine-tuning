import service from '@/api/request'
import { downloadFile } from '@/utils/download'

/**
 * 数据集管理接口（已对接后端 FastAPI）。
 * 页面组件无需改动，函数签名与原 mock 版本保持一致。
 * 其余模块仍走 mock，待后端逐模块上线后按此文件方式切换。
 */

export function getDatasetList(params = {}) {
  return service.get('/dataset/list', { params })
}

// 数据集类型字典。默认仅启用项（供导入下拉/规则表单）；管理页传 false 取全部
export function getDatasetTypes(enabledOnly = true) {
  return service.get('/dataset/types', { params: { enabledOnly } })
}

// 新建/更新数据集类型
export function saveDatasetType(payload) {
  return service.post('/dataset/types', payload)
}

// 启停数据集类型
export function setDatasetTypeStatus(id, enabled) {
  return service.put(`/dataset/types/${id}/status`, { enabled })
}

// 删除数据集类型（被转换规则引用时后端拒绝）
export function deleteDatasetType(id) {
  return service.delete(`/dataset/types/${id}`)
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

// 编辑脱敏规则（部分更新：field/maskType/pattern/replacement 等）
export function updateDesensitizeRule(id, payload) {
  return service.put(`/dataset/desensitize-rules/${id}`, payload)
}

// 删除脱敏规则
export function deleteDesensitizeRule(id) {
  return service.delete(`/dataset/desensitize-rules/${id}`)
}

// 执行脱敏（对最新原始文件真实掩码，写出脱敏文件并推进阶段）
export function runDesensitize(datasetId) {
  return service.post('/dataset/desensitize/run', { datasetId })
}

// 发布为可训练数据集（已脱敏 → 已发布 + 定版）。
// ratios: { trainRatio, valRatio, testRatio } 百分比，默认 80/10/10；训练读 train(+val)、评估读 test。
export function publishDataset(datasetId, ratios) {
  return service.post(`/dataset/${datasetId}/publish`, ratios)
}

// 下载该数据集最终训练数据（发布后的 alpaca jsonl）。
// variant=ner/relation 可下载对应子类型（如「实体关系标注」分出的 命名实体 / 关系三元组）。
export function downloadTrainData(datasetId, variant = '', split = 'train') {
  const params = {}
  if (variant) params.variant = variant
  if (split) params.split = split
  return downloadFile(`/dataset/${datasetId}/train-data/download`, {
    params,
    fallback: `${variant ? variant + '_' : ''}${split}-ds${datasetId}.jsonl`
  })
}

// 试脱敏：用当前启用规则对文本脱敏（只读），供脱敏对比预览
export function previewDesensitize(text) {
  return service.post('/dataset/desensitize/preview', { text })
}

export function getAnnotationTasks(params = {}) {
  return service.get('/dataset/annotation-tasks', { params })
}

// 提交标注进度（旧的手动整任务进度，逐样本标注改用 saveSampleLabel）
export function updateAnnotationProgress(taskId, done) {
  return service.put(`/dataset/annotation-tasks/${taskId}/progress`, { done })
}

// 逐样本主干：拉取某数据集的样本（含 raw/labeled/masked/status）
export function getDatasetSamples(datasetId, params = {}) {
  return service.get(`/dataset/${datasetId}/samples`, { params })
}

// 保存一条样本的标注结果（labeled 为结构化字段对象）
export function saveSampleLabel(sampleId, labeled) {
  return service.put(`/dataset/samples/${sampleId}`, { labeled })
}

// 复核标注任务：approved=true 通过（数据集进「已标注」），false 退回重标
export function reviewAnnotation(taskId, approved) {
  return service.put(`/dataset/annotation-tasks/${taskId}/review`, { approved })
}

// 删除标注任务（仅删跟踪行，不影响数据集与样本）
export function deleteAnnotationTask(taskId) {
  return service.delete(`/dataset/annotation-tasks/${taskId}`)
}

export function getDatasetVersions(datasetId) {
  return service.get('/dataset/versions', { params: { datasetId } })
}

// 新建数据集版本（payload: { datasetId, desc, version? }；version 不传则自动顺延）
export function createDatasetVersion(payload) {
  return service.post('/dataset/versions', payload)
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
