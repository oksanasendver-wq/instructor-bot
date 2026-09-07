import { useState } from 'react'
import type { TrendPeriod, TrendPoint } from './scoreTrend'
import { schoolDate, selectTrendPoints, trendDelta, trendPeriods } from './scoreTrend'
import './profile.css'

const contexts = [
  { value: 'training_ground', label: 'Площадка' },
  { value: 'city', label: 'Город' },
  { value: 'overall', label: 'Общая готовность' },
]

export function ScoreTrend({
  history,
  timezone = 'Asia/Almaty',
  today,
}: {
  history: TrendPoint[]
  timezone?: string
  today?: string
}) {
  const [period, setPeriod] = useState<TrendPeriod>('3m')
  const [context, setContext] = useState(
    history.some((p) => p.context === 'overall')
      ? 'overall'
      : history.some((p) => p.context === 'training_ground')
        ? 'training_ground'
        : 'city',
  )
  const points = selectTrendPoints(
    history,
    context,
    period,
    today || schoolDate(new Date(), timezone),
    timezone,
  )
  const delta = trendDelta(points)
  const label = contexts.find((item) => item.value === context)!.label
  const formatDate = (value: string) =>
    new Intl.DateTimeFormat('ru-RU', {
      timeZone: timezone,
      day: 'numeric',
      month: 'short',
    }).format(new Date(value.length === 10 ? value + 'T12:00:00Z' : value))
  const firstTime = points.length ? Date.parse(points[0].date) : 0
  const duration = points.length ? Date.parse(points[points.length - 1].date) - firstTime : 0
  const x = (point: TrendPoint) =>
    duration ? 30 + ((Date.parse(point.date) - firstTime) / duration) * 278 : 169
  const y = (point: TrendPoint) => 138 - point.score * 1.12
  return (
    <section className="card score-trend-card" aria-label="Динамика оценки вождения">
      <div className="row between">
        <h2>Динамика</h2>
      </div>
      <div className="score-trend-controls">
        <label>
          Показатель
          <select
            className="input"
            aria-label="Показатель на графике"
            value={context}
            onChange={(e) => setContext(e.target.value)}
          >
            {contexts.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          Период
          <select
            className="input"
            aria-label="Период динамики"
            value={period}
            onChange={(e) => setPeriod(e.target.value as TrendPeriod)}
          >
            {trendPeriods.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
        </label>
      </div>
      {!points.length ? (
        <p className="score-trend-message muted">
          За выбранный период нет оценок: {label.toLowerCase()}.
        </p>
      ) : points.length === 1 ? (
        <div className="score-trend-message">
          <p>
            Пока одна оценка. Для динамики нужны хотя бы два разных оценённых занятия в выбранном
            периоде.
          </p>
          <p className="small muted">
            {formatDate(points[0].date)} · {points[0].score} из 100
            {points[0].status ? ` · ${points[0].status}` : ''}
          </p>
        </div>
      ) : (
        <>
          <svg
            className="score-trend-chart"
            viewBox="0 0 320 158"
            role="img"
            aria-label={`${label}: оценки по ${points.length} занятиям, шкала от 0 до 100`}
          >
            {[0, 25, 50, 75, 100].map((value) => (
              <g key={value}>
                <line
                  x1="28"
                  x2="310"
                  y1={138 - value * 1.12}
                  y2={138 - value * 1.12}
                  stroke="var(--line)"
                  strokeDasharray="3 5"
                />
                <text x="0" y={141 - value * 1.12} fontSize="9" fill="var(--muted)">
                  {value}
                </text>
              </g>
            ))}
            {points
              .slice(1)
              .map(
                (point, index) =>
                  point.formula_version === points[index].formula_version && (
                    <line
                      key={`line:${index}`}
                      x1={x(points[index])}
                      y1={y(points[index])}
                      x2={x(point)}
                      y2={y(point)}
                      stroke="var(--blue)"
                      strokeWidth="2.5"
                    />
                  ),
              )}
            {points.map((point, index) => (
              <circle
                key={index}
                cx={x(point)}
                cy={y(point)}
                r="3.5"
                fill="var(--surface)"
                stroke="var(--blue)"
                strokeWidth="2"
              >
                <title>
                  {formatDate(point.date)}: {point.score} из 100
                  {point.status ? ` · ${point.status}` : ''}
                </title>
              </circle>
            ))}
          </svg>
          <div className="chart-labels">
            <span>{formatDate(points[0].date)}</span>
            <span>{formatDate(points[points.length - 1].date)}</span>
          </div>
          <p className="small score-trend-summary" aria-live="polite">
            {delta === null
              ? 'В периоде менялась методика. Изменение балла между версиями не сравнивается.'
              : delta === 0
                ? 'Без изменения балла за выбранный период.'
                : `${delta > 0 ? '+' : ''}${delta} балла за выбранный период.`}{' '}
            Оценённых занятий: {points.length}.
          </p>
        </>
      )}
      {points.length > 1 && (
        <details className="score-trend-table">
          <summary>Оценки по занятиям</summary>
          <table>
            <thead>
              <tr>
                <th>Дата</th>
                <th>Оценка</th>
                <th>Статус</th>
              </tr>
            </thead>
            <tbody>
              {points.map((point, index) => (
                <tr key={index}>
                  <td>{formatDate(point.date)}</td>
                  <td>{point.score}</td>
                  <td>
                    {point.status || '—'}
                    {point.formula_version != null && (
                      <small>Методика v{point.formula_version}</small>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </details>
      )}
    </section>
  )
}
