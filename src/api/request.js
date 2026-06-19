import axios from 'axios'
import { ElMessage } from 'element-plus'

/**
 * 统一的 axios 实例。
 * 原型阶段各 api 模块直接走本地 mock（见 src/mock）。
 * 联调时：把 mock 调用替换为 service.get/post 即可，拦截器已就绪。
 */
const service = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || '/api',
  timeout: 15000
})

// 请求拦截：注入 token
service.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) config.headers.Authorization = `Bearer ${token}`
    return config
  },
  (error) => Promise.reject(error)
)

// 响应拦截：统一处理后端 { code, data, message } 结构
service.interceptors.response.use(
  (response) => {
    const res = response.data
    if (res.code !== undefined && res.code !== 0 && res.code !== 200) {
      // 401：未登录/登录过期，清 token 并跳登录页
      if (res.code === 401) {
        localStorage.removeItem('token')
        if (!location.hash.includes('/login')) {
          location.hash = '#/login'
        }
      }
      ElMessage.error(res.message || '请求失败')
      return Promise.reject(new Error(res.message || 'Error'))
    }
    return res.data ?? res
  },
  (error) => {
    ElMessage.error(error.message || '网络异常')
    return Promise.reject(error)
  }
)

export default service
