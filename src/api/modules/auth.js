import service from '@/api/request'

/** 鉴权接口（已对接后端 FastAPI）。 */

export function login(data) {
  return service.post('/auth/login', data)
}

export function getCurrentUser() {
  return service.get('/auth/me')
}

export function logout() {
  return service.post('/auth/logout')
}
