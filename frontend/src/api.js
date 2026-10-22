import { auth } from './auth'

export class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.status = status
  }
}

export async function apiRequest(path, options = {}) {
  const method = (options.method || 'GET').toUpperCase()
  const headers = { ...(options.headers || {}) }
  if (options.body && !(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json'
  }
  if (!['GET', 'HEAD'].includes(method) && auth.csrfToken) {
    headers['X-CSRF-Token'] = auth.csrfToken
  }

  const response = await fetch(path, {
    credentials: 'include',
    ...options,
    method,
    headers,
  })

  if (response.status === 401) {
    auth.clear()
  }

  if (!response.ok) {
    let message = '请求失败，请稍后再试'
    try {
      const payload = await response.json()
      if (typeof payload.detail === 'string') {
        message = payload.detail
      } else if (Array.isArray(payload.detail)) {
        message = payload.detail.map((item) => item.msg).join('；')
      }
    } catch {
      message = response.statusText || message
    }
    throw new ApiError(message, response.status)
  }

  if (response.status === 204) {
    return null
  }
  return response.json()
}

export const get = (path) => apiRequest(path)
export const post = (path, body) =>
  apiRequest(path, { method: 'POST', body: body === undefined ? undefined : JSON.stringify(body) })
export const put = (path, body) =>
  apiRequest(path, { method: 'PUT', body: JSON.stringify(body) })
export const patch = (path, body) =>
  apiRequest(path, { method: 'PATCH', body: JSON.stringify(body) })
export const del = (path) => apiRequest(path, { method: 'DELETE' })
