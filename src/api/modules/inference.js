import service from '@/api/request'

/**
 * 模型推理 / 对话对比接口（评估模块「模型对话对比」页）。
 * 手选基座或微调版本对话，并排比较微调前后效果。
 * 推理在后端独立 worker 子进程中执行，首次加载某模型耗时较长，故 chat 超时放宽到 10 分钟。
 */

// 可选模型：离线基座 + 有真实产物的微调版本
export function getInferModels() {
  return service.get('/inference/models')
}

// 单轮对话（payload: { modelId, messages, maxTokens, temperature, topP, enableThinking }）
export function inferChat(payload) {
  return service.post('/inference/chat', payload, { timeout: 600000 })
}

// 当前常驻的推理 worker（已占显存）
export function getLoadedModels() {
  return service.get('/inference/loaded')
}

// 卸载一个已加载模型，释放显存
export function unloadModel(key) {
  return service.post('/inference/unload', { key })
}
