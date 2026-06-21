import service from '@/api/request'

/**
 * 微调配置管理接口（已对接后端 FastAPI）。
 * 页面组件无需改动，函数签名与原 mock 版本保持一致。
 */

// 基础模型库
export function getBaseModels(params = {}) {
  return service.get('/config/base-models', { params })
}

export function saveBaseModel(payload) {
  return service.post('/config/base-models', payload)
}

// 超参模板
export function getHyperTemplates(params = {}) {
  return service.get('/config/hyper-templates', { params })
}

export function saveHyperTemplate(payload) {
  return service.post('/config/hyper-templates', payload)
}

export function deleteHyperTemplate(id) {
  return service.delete(`/config/hyper-templates/${id}`)
}

// 训练资源配额
export function getResourceQuotas() {
  return service.get('/config/resource-quotas')
}

// 保存部门资源配额（quotas: [{ dept, gpuQuota, maxDuration, maxConcurrent }]）
export function saveResourceQuotas(quotas = []) {
  return service.post('/config/resource-quotas', { quotas })
}

// 自动调优配置
export function getAutoTuneConfig() {
  return service.get('/config/autotune')
}

// 保存并启动自动调优（cfg: { enabled, objective, searchAlgo, maxTrials, parallelTrials }）
export function saveAutoTuneConfig(cfg) {
  return service.post('/config/autotune', cfg)
}

// 操作权限配置
export function getRolePermissions() {
  return service.get('/config/role-permissions')
}

// 入参为权限矩阵 { 角色: { 权限名: 是否勾选 } }，转换为后端期望的 roles 列表
export function saveRolePermissions(matrix = {}) {
  const roles = Object.keys(matrix).map((role) => ({
    role,
    granted: Object.keys(matrix[role]).filter((perm) => matrix[role][perm])
  }))
  return service.post('/config/role-permissions', { roles })
}
