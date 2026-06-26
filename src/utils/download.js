import axios from 'axios'
import { ElMessage } from 'element-plus'

/**
 * 文件下载工具。
 * 后端下载接口返回二进制流（responseType: blob），无法走统一的 JSON 响应拦截器，
 * 故这里用独立 axios 调用，手动注入 token、解析文件名并触发浏览器保存。
 */
const baseURL = import.meta.env.VITE_API_BASE || '/api'

function parseFilename(disposition = '', fallback = 'download') {
  // 优先取 RFC5987 的 filename*（支持中文），否则取普通 filename
  const star = /filename\*=(?:UTF-8'')?([^;]+)/i.exec(disposition)
  if (star) return decodeURIComponent(star[1].replace(/["']/g, ''))
  const plain = /filename="?([^";]+)"?/i.exec(disposition)
  return plain ? decodeURIComponent(plain[1]) : fallback
}

function saveBlob(blob, filename) {
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  window.URL.revokeObjectURL(url)
}

/**
 * 下载并保存文件。
 * @param {string} url 相对接口路径（不含 /api 前缀）
 * @param {object} opts { method, params, data, fallback }
 */
export async function downloadFile(url, { method = 'get', params, data, fallback = 'download' } = {}) {
  const token = localStorage.getItem('token')
  const resp = await axios({
    url: baseURL + url,
    method,
    params,
    data,
    responseType: 'blob',
    headers: token ? { Authorization: `Bearer ${token}` } : {}
  })
  const blob = resp.data
  // 后端出错时会回传 JSON（被包成 blob），需识别并提示。
  // 精确匹配 mime（剥离 charset 等参数），避免把 application/jsonl 等误判成 JSON 错误。
  const mime = (blob.type || '').split(';')[0].trim().toLowerCase()
  if (mime === 'application/json') {
    const text = await blob.text()
    let msg = '下载失败'
    try { msg = JSON.parse(text).message || msg } catch (e) { /* ignore */ }
    ElMessage.error(msg)
    throw new Error(msg)
  }
  const filename = parseFilename(resp.headers['content-disposition'], fallback)
  saveBlob(blob, filename)
  return filename
}
