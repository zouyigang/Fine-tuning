import { mockRequest, paginate, genId, randomOf, randomInt, randomFloat } from '@/utils/mock'

// 评估任务列表
export function getEvalList(params = {}) {
  const list = Array.from({ length: 18 }).map((_, i) => ({
    id: genId(),
    model: `${randomOf(['实体识别', '关系抽取', 'OCR 识别', '事件构建'])}-v${randomInt(1, 6)}.${randomInt(0, 9)}`,
    modelType: randomOf(['实体识别', '关系抽取', 'OCR 识别', '事件构建']),
    dataset: `测试集-2026${String(i + 1).padStart(3, '0')}`,
    f1: randomFloat(0.85, 0.97, 3),
    precision: randomFloat(0.86, 0.98, 3),
    recall: randomFloat(0.83, 0.96, 3),
    status: randomOf(['已完成', '评估中']),
    evalAt: `2026-06-0${randomInt(1, 9)} 1${randomInt(0, 5)}:20`
  }))
  return mockRequest(paginate(list, params))
}

// 自动化指标（按模型类型）
export function getMetrics(modelType = 'ner') {
  const map = {
    ocr: [
      { name: '字符准确率', value: 98.6, unit: '%' },
      { name: '行准确率', value: 95.2, unit: '%' },
      { name: '平均编辑距离', value: 0.04, unit: '' },
      { name: '推理耗时', value: 42, unit: 'ms' }
    ],
    ner: [
      { name: '精确率', value: 94.8, unit: '%' },
      { name: '召回率', value: 92.3, unit: '%' },
      { name: 'F1 值', value: 93.5, unit: '%' },
      { name: '实体类型数', value: 12, unit: '类' }
    ],
    relation: [
      { name: '三元组准确率', value: 89.7, unit: '%' },
      { name: '关系召回率', value: 87.1, unit: '%' },
      { name: 'F1 值', value: 88.4, unit: '%' },
      { name: '关系类型数', value: 8, unit: '类' }
    ],
    event: [
      { name: '事件识别准确率', value: 91.2, unit: '%' },
      { name: '要素抽取 F1', value: 88.9, unit: '%' },
      { name: '触发词准确率', value: 90.5, unit: '%' },
      { name: '事件类型数', value: 6, unit: '类' }
    ]
  }
  return mockRequest({
    metrics: map[modelType] || map.ner,
    // 各实体/关系类别的细分指标
    perClass: [
      { label: '人名', precision: 96.2, recall: 95.1, f1: 95.6 },
      { label: '组织机构', precision: 93.4, recall: 91.0, f1: 92.2 },
      { label: '时间', precision: 97.8, recall: 96.5, f1: 97.1 },
      { label: '地点', precision: 92.1, recall: 89.7, f1: 90.9 },
      { label: '金额', precision: 95.5, recall: 94.2, f1: 94.8 },
      { label: '案由', precision: 86.3, recall: 82.5, f1: 84.4 }
    ]
  })
}

// 基准对比
export function getBenchmark() {
  const dims = ['精确率', '召回率', 'F1 值', '推理速度', '鲁棒性']
  return mockRequest({
    dims,
    models: [
      { name: '本次微调模型', values: [94.8, 92.3, 93.5, 88, 90] },
      { name: '当前生产模型', values: [91.2, 88.5, 89.8, 90, 85] },
      { name: '历史最优模型', values: [93.0, 90.1, 91.5, 85, 88] }
    ],
    compare: dims.map((d, i) => ({
      dim: d,
      current: [94.8, 92.3, 93.5, 88, 90][i],
      prod: [91.2, 88.5, 89.8, 90, 85][i],
      diff: +([94.8, 92.3, 93.5, 88, 90][i] - [91.2, 88.5, 89.8, 90, 85][i]).toFixed(1)
    }))
  })
}

// 真实业务场景验证
export function getSceneValidation() {
  return mockRequest({
    summary: { total: 1280, correct: 1186, accuracy: 92.7, hardCase: 156, hardAccuracy: 78.2 },
    cases: Array.from({ length: 10 }).map((_, i) => ({
      id: genId(),
      caseNo: `（2026）刑侦字第 ${randomInt(100, 999)} 号`,
      type: randomOf(['盗窃', '诈骗', '涉毒', '经济犯罪']),
      sampleCount: randomInt(50, 200),
      accuracy: randomFloat(85, 97, 1),
      hard: Math.random() > 0.6
    }))
  })
}

// 人工复核
export function getReviewSamples(params = {}) {
  const list = Array.from({ length: 20 }).map((_, i) => ({
    id: genId(),
    content: randomOf([
      '2026年3月，犯罪嫌疑人李某在朝阳区某银行转账50万元至王某账户',
      '经讯问，张某对盗窃东城区某商铺财物的事实供认不讳',
      '涉案账户 6217**** 于2月15日发生多笔异常大额交易'
    ]),
    modelOutput: randomOf(['实体: [李某/人名, 朝阳区/地点, 50万元/金额]', '事件: 盗窃(时间, 地点, 嫌疑人)', '关系: (李某, 转账, 王某)']),
    reviewer: randomOf(['办案民警-赵', '标注员-钱', '办案民警-孙']),
    result: randomOf(['正确', '正确', '正确', '错误', '待复核']),
    reviewedAt: `2026-06-0${randomInt(1, 9)}`
  }))
  return mockRequest(paginate(list, params))
}

export function getReviewSummary() {
  return mockRequest({ total: 500, reviewed: 420, correct: 389, accuracy: 92.6, pending: 80 })
}

// 错误案例分析
export function getErrorCases(params = {}) {
  const types = ['实体边界错误', '类型误判', '漏识别', '关系抽取错误', '事件要素缺失']
  let list = Array.from({ length: 25 }).map((_, i) => ({
    id: genId(),
    errorType: randomOf(types),
    content: '犯罪嫌疑人在2026年初多次往返于江浙沪一带',
    expected: '时间: 2026年初',
    actual: '时间: 2026年',
    modelType: randomOf(['实体识别', '关系抽取', '事件构建']),
    count: randomInt(1, 30)
  }))
  if (params.errorType) list = list.filter((e) => e.errorType === params.errorType)
  return mockRequest({
    ...paginate(list, params),
    dist: types.map((t) => ({ name: t, value: randomInt(10, 80) }))
  })
}

// 评估报告
export function getReportList(params = {}) {
  const list = Array.from({ length: 12 }).map((_, i) => ({
    id: genId(),
    name: `模型评估报告-${randomOf(['实体识别', 'OCR', '关系抽取'])}-v${randomInt(1, 6)}.${randomInt(0, 9)}`,
    model: `model-v${randomInt(1, 6)}.${randomInt(0, 9)}`,
    f1: randomFloat(0.85, 0.97, 3),
    conclusion: randomOf(['建议上线', '建议优化后上线', '不建议上线']),
    creator: randomOf(['张三', '李四']),
    createdAt: `2026-06-0${randomInt(1, 9)}`,
    status: randomOf(['已生成', '待审批', '已审批'])
  }))
  return mockRequest(paginate(list, params))
}
