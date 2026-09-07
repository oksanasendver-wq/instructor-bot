export type TrendPeriod = '3d' | '1w' | '1m' | '3m'
export interface TrendPoint {
  score: number
  context: string
  date: string
  booking_id?: number
  report_id?: number
  formula_version?: number
  status?: string
}

export const trendPeriods: { value: TrendPeriod; label: string }[] = [
  { value: '3d', label: '3 дня' },
  { value: '1w', label: 'Неделя' },
  { value: '1m', label: 'Месяц' },
  { value: '3m', label: '3 месяца' },
]

export function schoolDate(value: string | Date, timezone: string): string {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: timezone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(typeof value === 'string' ? new Date(value) : value)
}

export function periodStart(today: string, period: TrendPeriod): string {
  const date = new Date(today + 'T00:00:00Z')
  if (period === '3d' || period === '1w') {
    date.setUTCDate(date.getUTCDate() - (period === '3d' ? 2 : 6))
  } else {
    const day = date.getUTCDate()
    date.setUTCDate(1)
    date.setUTCMonth(date.getUTCMonth() - (period === '1m' ? 1 : 3))
    const lastDay = new Date(
      Date.UTC(date.getUTCFullYear(), date.getUTCMonth() + 1, 0),
    ).getUTCDate()
    date.setUTCDate(Math.min(day, lastDay))
  }
  return date.toISOString().slice(0, 10)
}

export function selectTrendPoints(
  history: TrendPoint[],
  context: string,
  period: TrendPeriod,
  today: string,
  timezone: string,
): TrendPoint[] {
  const start = periodStart(today, period)
  const lessons = new Map<string, TrendPoint>()
  for (const point of history) {
    if (
      point.context !== context ||
      !Number.isFinite(point.score) ||
      point.score < 0 ||
      point.score > 100
    )
      continue
    if (!Number.isFinite(new Date(point.date).getTime())) continue
    const day = point.date.length === 10 ? point.date : schoolDate(point.date, timezone)
    if (day < start || day > today) continue
    const key =
      point.booking_id != null
        ? `booking:${point.booking_id}`
        : point.report_id != null
          ? `report:${point.report_id}`
          : `date:${point.date}`
    lessons.set(key, point)
  }
  return [...lessons.values()].sort((a, b) => Date.parse(a.date) - Date.parse(b.date))
}

export function trendDelta(points: TrendPoint[]): number | null {
  if (points.length < 2) return null
  if (points.some((point) => point.formula_version !== points[0].formula_version)) return null
  return Math.round((points[points.length - 1].score - points[0].score) * 100) / 100
}
