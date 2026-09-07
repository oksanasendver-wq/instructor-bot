export interface Person {
  id: number
  full_name: string
  phone: string
  transmission?: string | null
  is_active?: boolean
  telegram_user_id?: number | null
  notes_internal?: string | null
  created_at?: string
}
export interface Booking {
  id: number
  client: Person
  instructor?: Person
  date: string
  start_at: string
  end_at: string
  duration_minutes: number
  context: string
  transmission: string
  status: string
  payment_type: string
  amount_due: number
  payment_status: string
  admin_comment?: string
  actions: string[]
  report_id: number | null
  overall_grade: number | null
  can_edit_report: boolean
  edited_until?: string
}
export interface Score {
  score: number | null
  status: string
  delta?: number | null
  formula_version?: number | null
  calculated_at?: string | null
  details: { [key: string]: unknown; skills?: SkillLevel[] }
}
export interface SkillLevel {
  id: number
  name: string
  level: number
  values: number[]
  weight: number
  is_core: boolean
}
export interface Flag {
  id: number
  client_id: number
  client_name?: string
  reason: string
  context: string
  active: boolean
  opened_at: string
  closed_at?: string
  closed_reason?: string
}
export interface HistoryItem {
  booking_id: number
  date: string
  start_at: string
  end_at: string
  status: string
  context: string
  instructor: string
  instructor_id: number
  report_id: number | null
  overall_grade: number | null
  autonomy_level: string | null
  quick_verdict: string | null
  comment_internal: string | null
  critical: boolean
  can_edit: boolean
  duration_minutes?: number
  exercises?: { exercise_id?: number; name: string; section?: string }[]
  skills?: { skill_id: number; value: number; name: string | null; version: number }[]
  created_at?: string | null
  last_edited_at?: string | null
  formula_version?: number | null
  interventions?: { type: string; reason?: string; description?: string; is_critical: boolean }[]
}
export interface Profile {
  timezone?: string
  server_now?: string
  client: Person
  stats: {
    total_lessons: number
    ground_lessons: number
    city_lessons: number
    no_show: number
    total_hours?: number
  }
  scores: { ground: Score; city: Score; overall: Score }
  history: HistoryItem[]
  flags: Flag[]
  score_history: ScoreHistoryPoint[]
  conclusions: {
    id: number
    text: string
    status: string
    version: number
    created_at: string
    approved_by_type?: string
    approved_by_id?: number
    approved_by_name?: string | null
    ai_draft_id?: number | null
  }[]
}
export interface ScoreHistoryPoint {
  score: number
  context: string
  date: string
  booking_id: number
  report_id: number
  status: string
  formula_version: number
  calculated_at: string
}
export interface CatalogItem {
  id: number
  name?: string
  short_name?: string
  official_name?: string
  context?: string
  weight?: number
  is_core?: boolean
  active?: boolean
  paper_section?: string
  sort_order?: number
  version?: number
}
export interface ReportInput {
  context: string
  exercises: { exercise_id: number }[]
  skills: { skill_id: number; value: number }[]
  overall_grade_1_5: number
  autonomy_level: string
  intervention: { type: string; reason?: string; description?: string; is_critical: boolean }
  quick_verdict?: string
  comment_internal?: string
}
export interface ReportResult {
  report_id: number
  scores: { ground: number | null; city: number | null; overall: number | null }
  edited_until: string
}
export const contextLabel = (context: string) =>
  (
    ({
      'Учебная площадка': 'Площадка',
      training_ground: 'Площадка',
      Город: 'Город',
      city: 'Город',
      overall: 'Общий',
    }) as Record<string, string>
  )[context] ||
  context ||
  'Контекст не указан'
export const statusLabels: Record<string, string> = {
  planned: 'Запланировано',
  arrival_window: 'Ожидаем ученика',
  in_progress: 'Идёт занятие',
  assessment_required: 'Нужна оценка',
  completed: 'Завершено',
  no_show: 'Неявка',
  admin_review_required: 'Нужен разбор',
}
export const dateLabel = (value: string, options?: Intl.DateTimeFormatOptions) =>
  new Intl.DateTimeFormat('ru-RU', options || { day: 'numeric', month: 'long' }).format(
    new Date(value.length === 10 ? value + 'T12:00:00' : value),
  )
export const money = (value: number) =>
  new Intl.NumberFormat('ru-KZ', { maximumFractionDigits: 0 }).format(value) + ' ₸'
