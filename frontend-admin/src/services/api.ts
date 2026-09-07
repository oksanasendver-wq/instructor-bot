import axios from 'axios'
const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL?.replace(/\/$/, '') || '',
  timeout: 60000,
})
client.interceptors.request.use((config) => {
  const token = localStorage.getItem('admin_token')
  if (token) config.headers.Authorization = 'Bearer ' + token
  return config
})
client.interceptors.response.use(
  (r) => r,
  (e) => {
    if (e.response?.status === 401 && !e.config?.url?.includes('/auth/login')) {
      localStorage.removeItem('admin_token')
      window.dispatchEvent(new Event('admin-auth-change'))
    }
    return Promise.reject(e)
  },
)
export const adminApi = {
  get: async <T>(path: string, params?: object) =>
    (await client.get<T>('/admin' + path, { params })).data,
  post: async <T>(path: string, data?: unknown) =>
    (await client.post<T>('/admin' + path, data)).data,
  patch: async <T>(path: string, data: unknown) =>
    (await client.patch<T>('/admin' + path, data)).data,
  remove: async (path: string) => (await client.delete('/admin' + path)).data,
  async login(username: string, password: string) {
    const { data } = await client.post('/admin/auth/login', { username, password })
    localStorage.setItem('admin_token', data.access_token)
    window.dispatchEvent(new Event('admin-auth-change'))
  },
  logout() {
    localStorage.removeItem('admin_token')
    window.dispatchEvent(new Event('admin-auth-change'))
  },
}
