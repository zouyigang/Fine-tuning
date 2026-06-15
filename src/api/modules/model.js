import { mockRequest, paginate, genId, randomOf, randomInt, randomFloat } from '@/utils/mock'

const STATUS = ['evaluating', 'evaluated', 'gray', 'online', 'offline', 'archived']
const TYPES = ['OCR 识别', '实体识别', '关系抽取', '事件构建', '风险预警']

const models = Array.from({ length: 30 }).map((_, i) => {
  const status = randomOf(STATUS)
  return {
    id: genId(),
    name: `${randomOf(TYPES)}模型`,
    version: `v${randomInt(1, 6)}.${randomInt(0, 9)}`,
    modelType: randomOf(TYPES),
    dataset: `数据集-2026${String(i + 1).padStart(3, '0')}`,
    f1: randomFloat(0.85, 0.97, 3),
    size: `${randomFloat(0.5, 14, 1)} GB`,
    status,
    trainAt: `2026-0${randomInt(1, 6)}-${randomInt(10, 28)} 1${randomInt(0, 5)}:00`,
    creator: randomOf(['张三', '李四', '王五'])
  }
})

export function getModelList(params = {}) {
  let list = [...models]
  if (params.keyword) list = list.filter((m) => m.name.includes(params.keyword))
  if (params.status) list = list.filter((m) => m.status === params.status)
  if (params.modelType) list = list.filter((m) => m.modelType === params.modelType)
  return mockRequest(paginate(list, params))
}

export function updateModelStatus(id, status) {
  const m = models.find((x) => x.id === id)
  if (m) m.status = status
  return mockRequest({ success: true })
}

// 灰度发布监控
export function getGrayReleases() {
  return mockRequest([
    {
      id: genId(),
      name: '实体识别模型 v5.2',
      scope: '刑侦支队 / 朝阳分局',
      traffic: 20,
      requests: 12480,
      errorRate: 0.8,
      accuracy: 93.6,
      status: '灰度中',
      startAt: '2026-06-06 10:00'
    },
    {
      id: genId(),
      name: 'OCR 识别模型 v3.4',
      scope: '指定案件（专案 2026-018）',
      traffic: 10,
      requests: 3260,
      errorRate: 1.2,
      accuracy: 97.8,
      status: '灰度中',
      startAt: '2026-06-07 09:30'
    }
  ])
}

export function getGrayTrend() {
  return mockRequest({
    points: Array.from({ length: 12 }).map((_, i) => `${i * 2}:00`),
    accuracy: Array.from({ length: 12 }).map(() => randomFloat(91, 95, 1)),
    errorRate: Array.from({ length: 12 }).map(() => randomFloat(0.3, 1.5, 2))
  })
}

// 上线/回滚记录
export function getReleaseHistory() {
  return mockRequest([
    { id: 1, version: 'v5.2', action: '全量上线', operator: '审批管理员-王', time: '2026-06-08 15:00', status: '成功', note: '灰度验证 F1 93.5%，达标' },
    { id: 2, version: 'v5.1', action: '灰度上线', operator: '算法工程师-张', time: '2026-06-06 10:00', status: '成功', note: '20% 流量' },
    { id: 3, version: 'v5.0', action: '回滚', operator: '系统管理员-李', time: '2026-05-30 22:10', status: '成功', note: '线上误识别率升高，回滚至 v4.9' },
    { id: 4, version: 'v4.9', action: '全量上线', operator: '审批管理员-王', time: '2026-05-20 14:00', status: '成功', note: '' }
  ])
}

// 可回滚的稳定版本
export function getRollbackCandidates() {
  return mockRequest(
    models
      .filter((m) => ['online', 'offline'].includes(m.status))
      .slice(0, 6)
      .map((m) => ({ ...m, stable: m.f1 > 0.9 }))
  )
}

// 部署目标
export function getDeployTargets() {
  return mockRequest([
    { id: 1, name: '本地推理服务器集群', type: '本地', spec: '8 × A100', status: '在线', load: 42 },
    { id: 2, name: '昇腾 NPU 集群', type: 'NPU', spec: '16 × 昇腾910B', status: '在线', load: 67 },
    { id: 3, name: '政务云推理节点', type: '云环境', spec: '弹性 GPU', status: '在线', load: 28 },
    { id: 4, name: '边缘部署节点（分局）', type: '边缘', spec: '4 × T4', status: '离线', load: 0 }
  ])
}

export const EXPORT_FORMATS = ['ONNX', 'TorchScript', 'PMML', 'SavedModel', 'GGUF']

// 归档列表
export function getArchiveList(params = {}) {
  let list = models
    .filter((m) => ['offline', 'archived'].includes(m.status))
    .map((m) => ({ ...m, archivedAt: '2026-05-' + randomInt(10, 28), permanent: m.f1 > 0.93 }))
  return mockRequest(paginate(list, params))
}
