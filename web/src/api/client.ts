import axios from 'axios'
import { ElMessage } from 'element-plus'

export interface ApiEnvelope<T> {
  code: number
  message: string
  data: T
}

const http = axios.create({
  baseURL: '/api',
  timeout: 30_000
})

http.interceptors.response.use(
  (res) => {
    const body = res.data as ApiEnvelope<unknown>
    if (body && typeof body === 'object' && 'code' in body && body.code !== 0) {
      ElMessage.error(body.message || '请求失败')
      return Promise.reject(new Error(body.message))
    }
    return res
  },
  (err) => {
    const detail = err?.response?.data?.detail
    ElMessage.error(detail || err.message || '网络异常')
    return Promise.reject(err)
  }
)

/** 直接拿到 data 字段，调用方不用每次解包 */
export async function get<T>(url: string, params?: Record<string, unknown>): Promise<T> {
  const res = await http.get<ApiEnvelope<T>>(url, { params })
  return res.data.data
}

export async function post<T>(url: string, body?: unknown): Promise<T> {
  const res = await http.post<ApiEnvelope<T>>(url, body)
  return res.data.data
}

export async function put<T>(url: string, body?: unknown): Promise<T> {
  const res = await http.put<ApiEnvelope<T>>(url, body)
  return res.data.data
}

export async function patch<T>(url: string, body?: unknown): Promise<T> {
  const res = await http.patch<ApiEnvelope<T>>(url, body)
  return res.data.data
}

export async function del<T>(url: string): Promise<T> {
  const res = await http.delete<ApiEnvelope<T>>(url)
  return res.data.data
}

export async function postForm<T>(url: string, form: FormData): Promise<T> {
  const res = await http.post<ApiEnvelope<T>>(url, form, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
  return res.data.data
}

export default http
