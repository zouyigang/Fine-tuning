import { mockRequest, paginate, genId, randomOf, randomInt, randomFloat } from '@/utils/mock'

const STATUS = ['pending', 'running', 'paused', 'success', 'failed']
const MODELS = ['OCR 识别', '实体识别', '关系抽取', '事件构建', '风险预警', '路径分析']

const tasks = Array.from({ length: 24 }).map((_, i) => {
  const status = randomOf(STATUS)
  return {
    id: genId(),
    name: `${randomOf(MODELS)}微调-${20260600 + i}`,
    modelType: randomOf(MODELS),
    baseModel: randomOf(['Qwen2-7B', 'Llama3-8B', '公安基座 v3', 'GLM4-9B']),
    dataset: `审讯笔录数据集-2026${String(i + 1).padStart(3, '0')}`,
    status,
    progress: status === 'success' ? 100 : status === 'running' ? randomInt(10, 95) : randomInt(0, 60),
    priority: randomOf(['高', '中', '低']),
    gpu: `${randomInt(1, 4)} × A100`,
    epoch: `${randomInt(1, 10)}/10`,
    loss: randomFloat(0.05, 0.6),
    creator: randomOf(['张三', '李四', '王五']),
    createdAt: `2026-06-0${randomInt(1, 9)} 0${randomInt(1, 9)}:30`,
    duration: `${randomInt(1, 12)}h ${randomInt(1, 59)}m`
  }
})

export function getTaskList(params = {}) {
  let list = [...tasks]
  if (params.keyword) list = list.filter((t) => t.name.includes(params.keyword))
  if (params.status) list = list.filter((t) => t.status === params.status)
  return mockRequest(paginate(list, params))
}

export function createTask(payload) {
  const item = { id: genId(), status: 'pending', progress: 0, loss: '-', ...payload }
  tasks.unshift(item)
  return mockRequest(item)
}

export function updateTaskStatus(id, status) {
  const t = tasks.find((x) => x.id === id)
  if (t) t.status = status
  return mockRequest({ success: true })
}

// 实时监控：单个运行中任务的指标
export function getRunningTask() {
  return mockRequest({
    id: 1001,
    name: '实体识别微调-20260608',
    status: 'running',
    progress: 68,
    epoch: '7/10',
    step: '13600/20000',
    eta: '约 42 分钟',
    gpuUtil: randomInt(78, 96),
    gpuMem: randomFloat(28, 38, 1),
    cpuUtil: randomInt(20, 45),
    curLoss: randomFloat(0.08, 0.15),
    curAcc: randomFloat(92, 96, 1)
  })
}

// 训练曲线（loss / acc）
export function getTrainingCurve() {
  const steps = Array.from({ length: 20 }).map((_, i) => (i + 1) * 1000)
  return mockRequest({
    steps,
    loss: steps.map((_, i) => +(0.85 * Math.exp(-i / 6) + 0.06 + Math.random() * 0.02).toFixed(3)),
    valLoss: steps.map((_, i) => +(0.9 * Math.exp(-i / 6) + 0.08 + Math.random() * 0.03).toFixed(3)),
    acc: steps.map((_, i) => +(60 + 36 * (1 - Math.exp(-i / 5)) + Math.random() * 1).toFixed(2)),
    gpu: steps.map(() => randomInt(75, 96))
  })
}

// 资源占用历史
export function getResourceUsage() {
  return mockRequest({
    points: Array.from({ length: 30 }).map((_, i) => `${i}s`),
    gpu: Array.from({ length: 30 }).map(() => randomInt(70, 98)),
    cpu: Array.from({ length: 30 }).map(() => randomInt(15, 50)),
    mem: Array.from({ length: 30 }).map(() => randomInt(40, 75))
  })
}

// 训练日志
export function getTaskLogs(params = {}) {
  const levels = ['INFO', 'WARN', 'ERROR', 'DEBUG']
  const msgs = [
    'Epoch 7 started, lr=2.0e-5',
    'step 13600 | loss=0.112 | acc=94.3%',
    'checkpoint saved at ./ckpt/epoch7-step13600.pt',
    'GPU memory usage 34.2GB / 40GB',
    'validation loss=0.108, f1=0.931',
    'WARN: gradient norm 5.21 exceeds threshold, clipping applied',
    'data loader prefetch 2 batches',
    'ERROR: NaN detected in loss, skipping batch 13721'
  ]
  let list = Array.from({ length: 60 }).map((_, i) => ({
    id: i,
    time: `2026-06-08 1${randomInt(0, 5)}:${String(randomInt(10, 59))}:${String(randomInt(10, 59))}`,
    level: randomOf(levels),
    msg: randomOf(msgs)
  }))
  if (params.level) list = list.filter((l) => l.level === params.level)
  if (params.keyword) list = list.filter((l) => l.msg.includes(params.keyword))
  return mockRequest(list)
}

// 批量调度队列
export function getScheduleQueue() {
  return mockRequest(
    tasks
      .filter((t) => ['pending', 'running'].includes(t.status))
      .slice(0, 8)
      .map((t, i) => ({ ...t, order: i + 1, scheduledAt: i < 2 ? '立即执行' : `2026-06-09 0${i}:00` }))
  )
}
