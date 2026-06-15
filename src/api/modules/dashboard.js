import { mockRequest, recentDates, randomInt } from '@/utils/mock'

export function getDashboardOverview() {
  return mockRequest({
    stats: [
      { label: '数据集总数', value: 28, unit: '个', icon: 'Coin', bg: '#2f54eb', trend: 12 },
      { label: '进行中微调任务', value: 6, unit: '个', icon: 'SetUp', bg: '#13c2c2', trend: 8 },
      { label: '已上线模型', value: 14, unit: '个', icon: 'Box', bg: '#52c41a', trend: 5 },
      { label: 'GPU 资源使用率', value: 66, unit: '%', icon: 'Cpu', bg: '#fa8c16', trend: -3 }
    ],
    taskTrend: {
      dates: recentDates(14),
      created: recentDates(14).map(() => randomInt(1, 8)),
      finished: recentDates(14).map(() => randomInt(1, 6))
    },
    modelTypeDist: [
      { name: '实体识别', value: 9 },
      { name: 'OCR 识别', value: 7 },
      { name: '关系抽取', value: 5 },
      { name: '事件构建', value: 4 },
      { name: '风险预警', value: 3 }
    ],
    recentTasks: [
      { name: '实体识别微调-20260608', status: 'running', progress: 68, creator: '张三' },
      { name: 'OCR 识别微调-20260607', status: 'success', progress: 100, creator: '李四' },
      { name: '关系抽取微调-20260606', status: 'success', progress: 100, creator: '王五' },
      { name: '风险预警微调-20260605', status: 'failed', progress: 42, creator: '张三' },
      { name: '事件构建微调-20260604', status: 'pending', progress: 0, creator: '赵六' }
    ],
    todos: [
      { type: '待审批', text: '实体识别模型 v5.2 全量上线申请', level: 'danger' },
      { type: '待评估', text: 'OCR 识别模型 v3.4 评估报告待生成', level: 'warning' },
      { type: '待复核', text: '80 条人工复核样本待处理', level: 'warning' },
      { type: '告警', text: '风险预警微调任务训练失败，需排查', level: 'danger' }
    ]
  })
}
