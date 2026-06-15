// 业务字典：模型类型、任务状态等（公安业务场景）
export const MODEL_TYPES = [
  { value: 'ocr', label: 'OCR 识别' },
  { value: 'ner', label: '实体识别' },
  { value: 'relation', label: '关系抽取' },
  { value: 'event', label: '事件构建' },
  { value: 'risk', label: '风险预警' },
  { value: 'path', label: '路径分析' }
]

export const DATA_TYPES = [
  { value: 'ocr', label: 'OCR 校对结果' },
  { value: 'entity', label: '实体关系标注' },
  { value: 'event', label: '事件标注' },
  { value: 'risk', label: '风险样本' }
]

export const BASE_MODELS = [
  { value: 'qwen2-7b', label: 'Qwen2-7B（开源）' },
  { value: 'qwen2-72b', label: 'Qwen2-72B（开源）' },
  { value: 'llama3-8b', label: 'Llama3-8B（开源）' },
  { value: 'gec-base', label: '公安原生-基座模型 v3' },
  { value: 'glm4-9b', label: 'GLM4-9B（开源）' }
]

export const TASK_STATUS = {
  pending: { label: '排队中', type: 'info' },
  running: { label: '训练中', type: 'primary' },
  paused: { label: '已暂停', type: 'warning' },
  success: { label: '已完成', type: 'success' },
  failed: { label: '失败', type: 'danger' }
}

export const MODEL_STATUS = {
  evaluating: { label: '待评估', type: 'info' },
  evaluated: { label: '已评估', type: 'warning' },
  gray: { label: '灰度中', type: 'primary' },
  online: { label: '已上线', type: 'success' },
  offline: { label: '已下线', type: 'info' },
  archived: { label: '已归档', type: 'info' }
}

export const DEPARTMENTS = ['刑侦支队', '经侦支队', '网安支队', '情报中心', '技术大队']

export const ROLES = ['普通用户', '标注人员', '算法工程师', '审批管理员', '系统管理员']

export const dictToTag = (dict, key) => dict[key] || { label: key, type: 'info' }
export const dictLabel = (list, value) =>
  list.find((i) => i.value === value)?.label || value
