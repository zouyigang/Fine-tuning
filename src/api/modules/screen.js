// import service from '@/api/request'

/**
 * 数据可视化大屏接口（当前为演示数据，后期对接后端只改本文件，不动页面）。
 *
 * 后期对接方式（保持函数签名不变）：
 *   export function getScreenData() {
 *     return service.get('/screen/overview')
 *   }
 * 后端可由各业务表实时聚合后按下方数据结构返回即可，前端 screen/index.vue 无需改动。
 */

const rand = (min, max) => Math.round(min + Math.random() * (max - min))
const randf = (min, max, d = 1) => +(min + Math.random() * (max - min)).toFixed(d)

// 近 N 天日期标签
function lastDays(n) {
  const arr = []
  const today = new Date()
  for (let i = n - 1; i >= 0; i--) {
    const d = new Date(today)
    d.setDate(today.getDate() - i)
    arr.push(`${d.getMonth() + 1}/${d.getDate()}`)
  }
  return arr
}

// 滚动日志样本：模拟平台实时操作流水
const ACTORS = ['admin', 'analyst', '李建国', 'approver', '王海', 'labeler', '张伟']
const ACTIONS = [
  { module: '微调任务', text: '创建任务「禁毒案情要素抽取-v3」', level: 'info' },
  { module: '数据集', text: '提交标注批次 B-2048（命名实体）', level: 'info' },
  { module: '模型上线', text: '灰度发布「反诈话术识别-v2」流量 20%', level: 'warn' },
  { module: '模型评估', text: '生成评估报告 RPT-7781（F1 0.93）', level: 'success' },
  { module: '数据集', text: '执行脱敏作业 DS-身份证号字段', level: 'info' },
  { module: '模型上线', text: '全量上线「警情分类-v5」', level: 'success' },
  { module: '微调任务', text: '任务 T-3092 触发断点续训', level: 'warn' },
  { module: '模型回滚', text: '回滚「图侦比对-v4 → v3」', level: 'danger' },
  { module: '配置管理', text: '保存超参模板「LoRA-r16-高精」', level: 'info' },
  { module: '模型评估', text: '提交人工复核 56 条（通过率 91%）', level: 'success' }
]

function buildLogs(n = 12) {
  const now = Date.now()
  return Array.from({ length: n }, (_, i) => {
    const a = ACTIONS[rand(0, ACTIONS.length - 1)]
    const t = new Date(now - i * rand(20, 180) * 1000)
    return {
      id: `${now}-${i}`,
      time: `${String(t.getHours()).padStart(2, '0')}:${String(t.getMinutes()).padStart(2, '0')}:${String(t.getSeconds()).padStart(2, '0')}`,
      actor: ACTORS[rand(0, ACTORS.length - 1)],
      module: a.module,
      text: a.text,
      level: a.level
    }
  })
}

const TASK_NAMES = [
  '禁毒案情要素抽取', '反诈话术识别', '警情智能分类', '图侦人像比对',
  '笔录摘要生成', '涉案物品识别', '舆情态势研判', '接处警语义理解'
]
const STATUS_POOL = ['running', 'running', 'finished', 'queued', 'failed']

function buildTasks(n = 8) {
  return Array.from({ length: n }, (_, i) => {
    const status = STATUS_POOL[rand(0, STATUS_POOL.length - 1)]
    return {
      id: `T-${3000 + i}`,
      name: `${TASK_NAMES[i % TASK_NAMES.length]}-v${rand(1, 6)}`,
      base: ['Qwen2-7B', 'GLM-4-9B', 'Baichuan2-13B', 'Llama3-8B'][rand(0, 3)],
      gpu: `${rand(1, 8)}×A100`,
      progress: status === 'finished' ? 100 : status === 'queued' ? 0 : rand(8, 96),
      loss: randf(0.18, 1.6, 3),
      status,
      eta: status === 'running' ? `${rand(5, 120)}min` : '—'
    }
  })
}

/**
 * 返回大屏全量快照。每次调用生成新的随机值，便于轮询刷新时呈现「实时跳动」效果。
 * 数据结构即未来后端 /screen/overview 的契约。
 */
export function getScreenData() {
  const dates = lastDays(14)
  const data = {
    // 顶部核心指标（带单位与同比）
    headline: [
      { key: 'datasets', label: '数据集总量', value: rand(1180, 1260), unit: '个', trend: randf(2, 9), up: true },
      { key: 'tasks', label: '累计微调任务', value: rand(3260, 3400), unit: '个', trend: randf(3, 12), up: true },
      { key: 'models', label: '在线服务模型', value: rand(42, 58), unit: '个', trend: randf(1, 6), up: true },
      { key: 'samples', label: '标注样本累计', value: rand(2380000, 2460000), unit: '条', trend: randf(4, 11), up: true }
    ],
    // 中部三大主指标（大号数字）
    spotlight: [
      { label: '今日训练任务', value: rand(28, 64), unit: '个', sub: `运行中 ${rand(6, 18)}` },
      { label: '模型平均准确率', value: randf(91.2, 96.8, 1), unit: '%', sub: `较上周 +${randf(0.3, 1.8)}` },
      { label: 'GPU 集群利用率', value: rand(62, 89), unit: '%', sub: `在用 ${rand(48, 72)}/96 卡` }
    ],
    // 微调任务趋势
    taskTrend: {
      dates,
      created: dates.map(() => rand(8, 42)),
      finished: dates.map(() => rand(6, 36))
    },
    // 数据集类型分布
    datasetDist: [
      { name: '文本分类', value: rand(280, 360) },
      { name: '命名实体', value: rand(220, 300) },
      { name: '问答对', value: rand(180, 260) },
      { name: '摘要生成', value: rand(120, 180) },
      { name: '图像识别', value: rand(90, 150) },
      { name: '多模态', value: rand(60, 110) }
    ],
    // 各警种标注进度 Top
    annotation: [
      { name: '刑侦', value: rand(78, 98) },
      { name: '禁毒', value: rand(70, 95) },
      { name: '经侦', value: rand(60, 92) },
      { name: '网安', value: rand(55, 90) },
      { name: '交管', value: rand(50, 88) }
    ],
    // 模型效果评估雷达（多维）
    radar: {
      indicators: [
        { name: '准确率', max: 100 }, { name: '召回率', max: 100 },
        { name: 'F1', max: 100 }, { name: '推理速度', max: 100 },
        { name: '鲁棒性', max: 100 }, { name: '泛化性', max: 100 }
      ],
      series: [
        { name: '微调后', value: [randf(90, 97), randf(88, 95), randf(89, 96), randf(80, 92), randf(85, 94), randf(82, 93)] },
        { name: '基线模型', value: [randf(72, 82), randf(70, 80), randf(71, 81), randf(74, 86), randf(68, 78), randf(66, 77)] }
      ]
    },
    // GPU 集群实时负载（每个节点）
    gpuNodes: Array.from({ length: 6 }, (_, i) => ({
      name: `Node-0${i + 1}`,
      util: rand(35, 98),
      mem: rand(40, 95)
    })),
    // 模型上线流水状态
    release: [
      { name: '反诈话术识别-v2', stage: '灰度', percent: rand(15, 45), color: '#faad14' },
      { name: '警情智能分类-v5', stage: '全量', percent: 100, color: '#52c41a' },
      { name: '图侦人像比对-v4', stage: '灰度', percent: rand(40, 70), color: '#faad14' },
      { name: '笔录摘要生成-v3', stage: '待审批', percent: rand(0, 10), color: '#1890ff' }
    ],
    logs: buildLogs(14),
    tasks: buildTasks(8)
  }
  return Promise.resolve(data)
}
