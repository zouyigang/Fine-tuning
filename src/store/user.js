import { defineStore } from 'pinia'
import { ref } from 'vue'
import { login as loginApi, getCurrentUser, logout as logoutApi } from '@/api/modules/auth'

// 当前登录用户：token 持久化到 localStorage，用户信息由 /auth/me 拉取
export const useUserStore = defineStore('user', () => {
  const token = ref(localStorage.getItem('token') || '')
  const userInfo = ref({ name: '', role: '', dept: '', avatar: '' })

  function setUser(u) {
    userInfo.value = { name: u.name || '', role: u.role || '', dept: u.dept || '', avatar: '' }
  }

  async function login(payload) {
    const res = await loginApi(payload)
    token.value = res.token
    localStorage.setItem('token', res.token)
    setUser(res.user)
    return res
  }

  async function getInfo() {
    const u = await getCurrentUser()
    setUser(u)
    return u
  }

  async function logout() {
    try {
      await logoutApi()
    } catch (e) {
      // 忽略登出接口异常，本地清理即可
    }
    token.value = ''
    userInfo.value = { name: '', role: '', dept: '', avatar: '' }
    localStorage.removeItem('token')
  }

  return { token, userInfo, login, getInfo, logout, setUser }
})
