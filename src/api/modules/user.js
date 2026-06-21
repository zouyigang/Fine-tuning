import service from '@/api/request'

/**
 * 用户管理接口（对接后端 FastAPI /user）。
 * 写操作受后端 RBAC 拦截（需「权限分配」权限），仅系统管理员/被授权角色可调。
 */

export function getUserList(params = {}) {
  return service.get('/user/list', { params })
}

export function createUser(payload) {
  return service.post('/user', payload)
}

export function updateUser(id, payload) {
  return service.put(`/user/${id}`, payload)
}

export function deleteUser(id) {
  return service.delete(`/user/${id}`)
}

export function resetPassword(id, password) {
  return service.post(`/user/${id}/reset-password`, { password })
}

export function setUserStatus(id, status) {
  return service.put(`/user/${id}/status`, { status })
}
