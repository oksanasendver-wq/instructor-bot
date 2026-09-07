import axios from 'axios'
import {
  Booking,
  Person,
  Profile,
  Flag,
  ReportInput,
  ReportResult,
  CatalogItem,
} from '../../../shared/types'
const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL?.replace(/\/$/, '') || '',
  timeout: 20000,
})
client.interceptors.request.use((config) => {
  const token = localStorage.getItem('instructor_token')
  if (token) config.headers.Authorization = 'Bearer ' + token
  return config
})
client.interceptors.response.use(
  (r) => r,
  (error) => {
    if (error.response?.status === 401 && !error.config?.url?.includes('/auth/')) {
      localStorage.removeItem('instructor_token')
      window.dispatchEvent(new Event('instructor-session-expired'))
    }
    return Promise.reject(error)
  },
)
const get = async <T>(path: string, params?: object) =>
  (await client.get<T>('/api/instructor' + path, { params })).data
const post = async <T>(path: string, data?: unknown) =>
  (await client.post<T>('/api/instructor' + path, data)).data
export interface InstructorProfile extends Person {
  timezone: string
  today: string
  school_time: string
  app_name: string
  app_version: string
}
export interface InstructorStatistics {
  total_lessons: number
  total_hours: number
  total_clients: number
  ground_lessons: number
  city_lessons: number
  no_show: number
  pending_reports: number
  reported_lessons: number
  average_grade: number | null
}
export interface LessonReport extends ReportInput {
  id: number
  booking_id: number
  can_edit: boolean
  skills: (ReportInput['skills'][number] & { name: string; version?: number })[]
  exercises: (ReportInput['exercises'][number] & { name: string; section?: string })[]
  interventions?: ReportInput['intervention'][]
  created_at?: string
  last_edited_at?: string
  formula_version?: string
}
export const api = {
  setToken(token: string) {
    localStorage.setItem('instructor_token', token)
  },
  authenticateTelegram: (initData: string) =>
    post<{ access_token: string; instructor: Person }>('/auth/telegram', { init_data: initData }),
  getMe: () => get<InstructorProfile>('/me'),
  getStatistics: () => get<InstructorStatistics>('/me/statistics'),
  getTodayBookings: () => get<Booking[]>('/bookings/me/today'),
  getBookings: (params?: object) => get<Booking[]>('/bookings', params),
  getBooking: (id: number) => get<Booking>('/bookings/' + id),
  markArrived: (id: number) => post('/bookings/' + id + '/arrived'),
  markNoShow: (id: number) => post('/bookings/' + id + '/no-show'),
  finishBooking: (id: number) => post('/bookings/' + id + '/finish'),
  payment: (id: number, received: boolean) => post('/bookings/' + id + '/payment', { received }),
  createReport: (id: number, data: ReportInput) =>
    post<ReportResult>('/bookings/' + id + '/report', data),
  updateReport: async (id: number, data: ReportInput) =>
    (await client.patch<ReportResult>('/api/instructor/reports/' + id, data)).data,
  getReport: (id: number) => get<LessonReport>('/reports/' + id),
  getClients: () => get<(Person & { active_flags: number })[]>('/clients'),
  getFlags: () => get<Flag[]>('/flags'),
  getClientProfile: (id: number) => get<Profile>('/clients/' + id + '/profile'),
  getClientHistory: (id: number) => get('/clients/' + id + '/history'),
  getExercises: (context: string) =>
    get<{ exercises: CatalogItem[] }>('/catalogs/exercises', { context }),
  getSkills: (context: string) => get<{ skills: CatalogItem[] }>('/catalogs/skills', { context }),
  getVerdicts: () => get<{ verdicts: CatalogItem[] }>('/catalogs/verdicts'),
  getInterventionReasons: (context: string) =>
    get<{ reasons: CatalogItem[] }>('/catalogs/intervention-reasons', { context }),
}
