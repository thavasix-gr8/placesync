export const API_URL = 'http://localhost:8000'

export async function apiRequest(path, options = {}) {
  const token = localStorage.getItem('token')
  const headers = { ...(options.headers || {}) }

  if (token) headers.Authorization = `Bearer ${token}`
  if (options.body && !headers['Content-Type']) headers['Content-Type'] = 'application/json'

  const response = await fetch(`${API_URL}${path}`, { ...options, headers })
  const data = response.status === 204 ? null : await response.json()

  if (!response.ok) {
    const message = typeof data.detail === 'string' ? data.detail : data.detail?.message
    throw new Error(message || 'Something went wrong. Please try again.')
  }
  return data
}
