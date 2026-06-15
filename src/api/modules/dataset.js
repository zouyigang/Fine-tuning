import { mockRequest, paginate, genId, randomOf, randomInt } from '@/utils/mock'
// import service from '@/api/request' // 联调时启用

const DATA_TYPES = ['OCR 校对结果', '实体关系标注', '事件标注', '风险样本']
const DEPTS = ['刑侦支队', '经侦支队', '网安支队', '情报中心']
const STATUS = ['标注中', '已完成', '待审核', '已归档']

// 数据集主表（模块内共享的内存数据）
const datasets = Array.from({ length: 28 }).map((_, i) => {
  const total = randomInt(2000, 50000)
  const labeled = randomInt(Math.floor(total * 0.4), total)
  return {
    id: genId(),
    name: `${randomOf(['审讯笔录', '资金流水', '案件卷宗', '涉案人员', '风险预警'])}数据集-${2026}${String(i + 1).padStart(3, '0')}`,
    type: randomOf(DATA_TYPES),
    dept: randomOf(DEPTS),
    total,
    labeled,
    progress: Math.round((labeled / total) * 100),
    version: `v1.${randomInt(0, 6)}`,
    desensitized: Math.random() > 0.3,
    status: randomOf(STATUS),
    owner: randomOf(['张三', '李四', '王五', '赵六']),
    updatedAt: `2026-0${randomInt(1, 6)}-${String(randomInt(10, 28))} 1${randomInt(0, 5)}:30`
  }
})

export function getDatasetList(params = {}) {
  let list = [...datasets]
  if (params.keyword) list = list.filter((d) => d.name.includes(params.keyword))
  if (params.type) list = list.filter((d) => d.type === params.type)
  if (params.status) list = list.filter((d) => d.status === params.status)
  return mockRequest(paginate(list, params))
  // 联调: return service.get('/dataset/list', { params })
}

export function getDatasetDetail(id) {
  return mockRequest(datasets.find((d) => d.id === id))
}

export function createDataset(payload) {
  const item = { id: genId(), progress: 0, labeled: 0, version: 'v1.0', status: '标注中', ...payload }
  datasets.unshift(item)
  return mockRequest(item)
}

export function deleteDataset(id) {
  const idx = datasets.findIndex((d) => d.id === id)
  if (idx > -1) datasets.splice(idx, 1)
  return mockRequest({ success: true })
}

// 脱敏规则
export function getDesensitizeRules() {
  return mockRequest([
    { id: 1, field: '身份证号', rule: '保留前6后4，中间*', sample: '110101********1234', enabled: true },
    { id: 2, field: '手机号', rule: '保留前3后4', sample: '138****8888', enabled: true },
    { id: 3, field: '银行卡号', rule: '仅保留后4位', sample: '**** **** **** 6789', enabled: true },
    { id: 4, field: '姓名', rule: '保留姓氏', sample: '张**', enabled: true },
    { id: 5, field: '家庭住址', rule: '保留到区县', sample: '北京市朝阳区****', enabled: false },
    { id: 6, field: '案件编号', rule: '哈希脱敏', sample: 'A1B2****E5F6', enabled: false }
  ])
}

// 标注任务
export function getAnnotationTasks(params = {}) {
  const list = Array.from({ length: 16 }).map((_, i) => ({
    id: genId(),
    title: `${randomOf(['审讯笔录', '资金流水', '通话记录'])}标注任务-${i + 1}`,
    type: randomOf(['OCR 文本校对', '实体/关系三元组', '事件要素', '风险行为']),
    total: randomInt(100, 800),
    done: randomInt(0, 100),
    annotators: randomInt(1, 5),
    status: randomOf(['进行中', '待审核', '已完成']),
    deadline: `2026-06-${randomInt(10, 30)}`
  }))
  return mockRequest(paginate(list, params))
}

// 版本管理
export function getDatasetVersions(datasetId) {
  return mockRequest([
    { version: 'v1.3', desc: '补充 3200 条风险样本，修正实体边界', author: '张三', count: 48200, time: '2026-06-05 14:20', current: true },
    { version: 'v1.2', desc: '完成关系三元组二次审核', author: '李四', count: 45000, time: '2026-05-22 09:10', current: false },
    { version: 'v1.1', desc: '新增事件要素标注', author: '王五', count: 41000, time: '2026-05-08 16:40', current: false },
    { version: 'v1.0', desc: '初始版本导入', author: '赵六', count: 32000, time: '2026-04-20 11:00', current: false }
  ])
}

// 统计分析
export function getDatasetStatistics(datasetId) {
  return mockRequest({
    overview: { total: 48200, labeled: 45120, quality: 96.4, balance: 78 },
    entityDist: [
      { name: '人名', value: 12400 },
      { name: '组织机构', value: 8600 },
      { name: '时间', value: 7200 },
      { name: '地点', value: 6800 },
      { name: '金额', value: 5400 },
      { name: '案由', value: 3200 }
    ],
    typeDist: [
      { name: 'OCR 校对', value: 18000 },
      { name: '实体关系', value: 15200 },
      { name: '事件标注', value: 9000 },
      { name: '风险样本', value: 6000 }
    ],
    suggestions: [
      '“案由”类实体样本偏少（占比 6.6%），建议补充至 5000 条以上以平衡分布',
      '风险样本中“资金异常”子类占比过高（72%），建议增加“身份异常”样本',
      '约 3080 条样本尚未标注，建议优先分配标注人员完成'
    ]
  })
}

// 权限控制
export function getDatasetPermissions(params = {}) {
  const list = datasets.slice(0, 12).map((d) => ({
    id: d.id,
    name: d.name,
    secret: d.desensitized ? '涉密' : '内部',
    dept: d.dept,
    roles: ['标注人员', '算法工程师'],
    canView: true,
    canEdit: Math.random() > 0.5,
    canExport: Math.random() > 0.6
  }))
  return mockRequest(paginate(list, params))
}
