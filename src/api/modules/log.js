import service from '@/api/request'

/**
 * 操作日志（审计）接口。
 * 后端中间件自动记录所有写操作（登录/建任务/改状态/上线回滚等），此处仅查询。
 */

export function getOperationLogs(params = {}) {
  return service.get('/log/list', { params })
}

export function getLogModules() {
  return service.get('/log/modules')
}
