import service from '@/api/request'
import { downloadFile } from '@/utils/download'

/**
 * 微调任务管理接口（已对接后端 FastAPI）。
 * 实时监控数据由后端「模拟训练调度器」周期写入 train_metric/train_log。
 * 页面组件无需改动，函数签名与原 mock 版本保持一致。
 */

export function getTaskList(params = {}) {
  return service.get('/task/list', { params })
}

export function createTask(payload) {
  return service.post('/task', payload)
}

export function updateTaskStatus(id, status) {
  return service.put(`/task/${id}/status`, { status })
}

// 实时监控：当前运行中任务的指标
export function getRunningTask() {
  return service.get('/task/running')
}

// 训练曲线（loss / acc）
export function getTrainingCurve() {
  return service.get('/task/curve')
}

// 资源占用历史
export function getResourceUsage() {
  return service.get('/task/resource-usage')
}

// 训练日志
export function getTaskLogs(params = {}) {
  return service.get('/task/logs', { params })
}

// 下载训练日志为 .log 文件（params: { level, keyword }）
export function downloadTaskLogs(taskId, params = {}) {
  return downloadFile(`/task/${taskId}/logs/download`, {
    params,
    fallback: `train-task-${taskId}.log`
  })
}

// GPU 实时状态（真实引擎模式；sim 模式返回占位）
export function getGpus() {
  return service.get('/task/gpus')
}

// 批量调度队列
export function getScheduleQueue() {
  return service.get('/task/schedule')
}

// 新建批量调度项（payload: { name, priority, gpu, scheduledAt }）
export function createScheduleItem(payload) {
  return service.post('/task/schedule', payload)
}

// 移除调度项
export function removeScheduleItem(id) {
  return service.delete(`/task/schedule/${id}`)
}

// 重排调度顺序（ids: 调度项 id 的目标顺序）
export function reorderSchedule(ids) {
  return service.put('/task/schedule/reorder', { ids })
}
