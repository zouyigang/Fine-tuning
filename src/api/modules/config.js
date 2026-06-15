import { mockRequest, paginate, genId, randomOf, randomInt } from '@/utils/mock'

// 基础模型库
const baseModels = [
  { id: genId(), name: 'Qwen2-7B', source: '开源', vendor: '阿里通义', params: '7B', license: 'Apache-2.0', useCount: 32, addedAt: '2026-03-10', enabled: true },
  { id: genId(), name: 'Qwen2-72B', source: '开源', vendor: '阿里通义', params: '72B', license: 'Apache-2.0', useCount: 8, addedAt: '2026-03-10', enabled: true },
  { id: genId(), name: 'Llama3-8B', source: '开源', vendor: 'Meta', params: '8B', license: 'Llama-3', useCount: 15, addedAt: '2026-02-22', enabled: true },
  { id: genId(), name: 'GLM4-9B', source: '开源', vendor: '智谱', params: '9B', license: 'GLM-License', useCount: 11, addedAt: '2026-04-01', enabled: true },
  { id: genId(), name: '公安基座模型 v3', source: '原生', vendor: '内部研发', params: '13B', license: '内部授权', useCount: 46, addedAt: '2026-01-15', enabled: true },
  { id: genId(), name: '第三方风控预训练模型', source: '第三方', vendor: '某安全厂商', params: '6B', license: '商业授权', useCount: 4, addedAt: '2026-05-12', enabled: false }
]

export function getBaseModels(params = {}) {
  let list = [...baseModels]
  if (params.source) list = list.filter((m) => m.source === params.source)
  return mockRequest(paginate(list, params))
}

export function saveBaseModel(payload) {
  if (payload.id) {
    Object.assign(baseModels.find((m) => m.id === payload.id) || {}, payload)
  } else {
    baseModels.unshift({ id: genId(), useCount: 0, enabled: true, addedAt: '2026-06-09', ...payload })
  }
  return mockRequest({ success: true })
}

// 超参模板
const templates = [
  { id: genId(), name: '审讯笔录实体识别模板', scene: '实体识别', lr: '2e-5', batchSize: 16, epochs: 8, optimizer: 'AdamW', useCount: 18 },
  { id: genId(), name: '资金流关系抽取模板', scene: '关系抽取', lr: '3e-5', batchSize: 8, epochs: 10, optimizer: 'AdamW', useCount: 9 },
  { id: genId(), name: 'OCR 校对微调模板', scene: 'OCR 识别', lr: '1e-4', batchSize: 32, epochs: 5, optimizer: 'Adam', useCount: 22 },
  { id: genId(), name: '风险预警分类模板', scene: '风险预警', lr: '2e-5', batchSize: 16, epochs: 6, optimizer: 'AdamW', useCount: 7 }
]

export function getHyperTemplates(params = {}) {
  return mockRequest(paginate([...templates], params))
}

export function saveHyperTemplate(payload) {
  if (payload.id) {
    Object.assign(templates.find((t) => t.id === payload.id) || {}, payload)
  } else {
    templates.unshift({ id: genId(), useCount: 0, ...payload })
  }
  return mockRequest({ success: true })
}

export function deleteHyperTemplate(id) {
  const idx = templates.findIndex((t) => t.id === id)
  if (idx > -1) templates.splice(idx, 1)
  return mockRequest({ success: true })
}

// 训练资源配额
export function getResourceQuotas() {
  return mockRequest({
    cluster: { totalGpu: 32, usedGpu: 21, totalCpu: 512, usedCpu: 280, runningTasks: 6, queuedTasks: 4 },
    quotas: [
      { dept: '刑侦支队', gpuQuota: 12, gpuUsed: 8, maxDuration: 48, maxConcurrent: 4 },
      { dept: '经侦支队', gpuQuota: 8, gpuUsed: 5, maxDuration: 24, maxConcurrent: 3 },
      { dept: '网安支队', gpuQuota: 6, gpuUsed: 4, maxDuration: 24, maxConcurrent: 2 },
      { dept: '情报中心', gpuQuota: 6, gpuUsed: 4, maxDuration: 36, maxConcurrent: 2 }
    ]
  })
}

// 自动调优配置
export function getAutoTuneConfig() {
  return mockRequest({
    enabled: true,
    objective: 'maximize_f1',
    searchAlgo: 'bayesian',
    maxTrials: 30,
    parallelTrials: 4,
    searchSpace: [
      { param: '学习率 (lr)', range: '1e-5 ~ 1e-3', type: 'log' },
      { param: '批次大小 (batch_size)', range: '8, 16, 32, 64', type: 'choice' },
      { param: '训练轮数 (epochs)', range: '3 ~ 12', type: 'int' },
      { param: 'warmup 比例', range: '0.0 ~ 0.1', type: 'float' }
    ],
    trials: Array.from({ length: 8 }).map((_, i) => ({
      trial: i + 1,
      lr: ['2e-5', '3e-5', '5e-5', '1e-4'][i % 4],
      batchSize: [16, 32, 8, 16][i % 4],
      epochs: randomInt(5, 10),
      f1: +(0.88 + Math.random() * 0.08).toFixed(3),
      status: i < 6 ? '已完成' : '运行中'
    }))
  })
}

// 操作权限配置
export function getRolePermissions() {
  const perms = ['创建微调任务', '配置超参数', '审批模型上线', '模型回滚', '数据集导出', '资源配额管理', '权限分配']
  return mockRequest({
    perms,
    roles: [
      { role: '普通用户', granted: ['创建微调任务'] },
      { role: '标注人员', granted: ['创建微调任务'] },
      { role: '算法工程师', granted: ['创建微调任务', '配置超参数', '数据集导出'] },
      { role: '审批管理员', granted: ['创建微调任务', '审批模型上线', '模型回滚'] },
      { role: '系统管理员', granted: perms }
    ]
  })
}

export function saveRolePermissions(payload) {
  return mockRequest({ success: true })
}
