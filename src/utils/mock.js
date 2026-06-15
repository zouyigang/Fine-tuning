/**
 * mock 请求模拟器：返回 Promise，模拟网络延迟。
 * 业务 api 模块统一通过它返回本地数据，联调时整体替换为真实 service 调用。
 */
export function mockRequest(data, delay = 300) {
  return new Promise((resolve) => {
    setTimeout(() => resolve(typeof data === 'function' ? data() : data), delay)
  })
}

let _id = 1000
export const genId = () => ++_id

export function paginate(list, { page = 1, pageSize = 10 } = {}) {
  const start = (page - 1) * pageSize
  return {
    list: list.slice(start, start + pageSize),
    total: list.length,
    page,
    pageSize
  }
}

// 随机工具
export const randomOf = (arr) => arr[Math.floor(Math.random() * arr.length)]
export const randomInt = (min, max) => Math.floor(Math.random() * (max - min + 1)) + min
export const randomFloat = (min, max, fixed = 2) =>
  (Math.random() * (max - min) + min).toFixed(fixed)

// 生成最近 n 天日期
export function recentDates(n) {
  const out = []
  const today = new Date('2026-06-09')
  for (let i = n - 1; i >= 0; i--) {
    const d = new Date(today)
    d.setDate(today.getDate() - i)
    out.push(`${d.getMonth() + 1}/${d.getDate()}`)
  }
  return out
}
