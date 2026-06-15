import { defineStore } from 'pinia'
import { ref } from 'vue'

// 当前登录用户（原型阶段为静态数据，联调后由登录接口写入）
export const useUserStore = defineStore('user', () => {
  const userInfo = ref({
    name: '张三',
    role: '算法工程师',
    dept: '刑侦支队 · 技术大队',
    avatar: ''
  })

  return { userInfo }
})
