import { Link } from 'react-router-dom'
import {
  ArrowUpRight,
  CalendarDays,
  CheckCheck,
  Flag as FlagIcon,
  ClipboardList,
  Plus,
  Activity,
} from 'lucide-react'
import { adminApi } from '../services/api'
import { Avatar, Empty, ErrorBox, Loading, Status, useResource } from '../components/UI'
import { Booking, Flag, contextLabel, dateLabel } from '../../../shared/types'
type Stats = {
  today: string
  total_bookings_today: number
  completed_today: number
  in_progress_today: number
  assessment_required: number
  no_show_today: number
  active_instructors: number
  total_clients: number
  active_flags: number
}
export default function DashboardPage() {
  const { data, error, loading, reload } = useResource(
    async () => {
      const stats = await adminApi.get<Stats>('/stats')
      const [bookings, flags, pending] = await Promise.all([
        adminApi.get<{ bookings: Booking[] }>('/bookings', {
          date_from: stats.today,
          date_to: stats.today,
        }),
        adminApi.get<Flag[]>('/attention-flags'),
        adminApi.get<{ bookings: Booking[] }>('/bookings', {
          status_filter: 'admin_review_required',
        }),
      ])
      return { stats, bookings: bookings.bookings, flags, pending: pending.bookings }
    },
    '',
    true,
  )
  if (loading && !data) return <Loading />
  return (
    <div className="stack">
      <div className="admin-heading">
        <div>
          <p className="eyebrow">
            {data
              ? dateLabel(data.stats.today, { weekday: 'long', day: 'numeric', month: 'long' })
              : 'Обзор школы'}
          </p>
          <h1>Школа в движении</h1>
          <p className="small muted">Всё, что важно для сегодняшней практики.</p>
        </div>
        <Link className="btn" to="/bookings">
          <Plus size={17} />
          Назначить занятие
        </Link>
      </div>
      <ErrorBox message={error} retry={reload} />
      {data && (
        <>
          <div className="admin-metrics">
            {[
              {
                label: 'Занятий сегодня',
                value: data.stats.total_bookings_today,
                icon: CalendarDays,
                color: 'blue',
                sub: data.stats.in_progress_today + ' идут прямо сейчас',
              },
              {
                label: 'Завершено',
                value: data.stats.completed_today,
                icon: CheckCheck,
                color: 'green',
                sub: 'с оценками инструктора',
              },
              {
                label: 'Ожидают отчёта',
                value: data.stats.assessment_required,
                icon: ClipboardList,
                color: 'amber',
                sub: 'нужно зафиксировать результат',
              },
              {
                label: 'Требуют внимания',
                value: data.stats.active_flags,
                icon: FlagIcon,
                color: 'red',
                sub: 'повторяющиеся трудности',
              },
            ].map((m) => (
              <div className="card dashboard-metric" key={m.label}>
                <div className="row between">
                  <span className="small muted">{m.label}</span>
                  <span className={'badge ' + m.color}>
                    <m.icon size={18} />
                  </span>
                </div>
                <strong>{m.value}</strong>
                <p className="small muted">{m.sub}</p>
              </div>
            ))}
          </div>
          <div className="dashboard-grid">
            <section className="card">
              <div className="section-heading">
                <h2>Занятия сегодня</h2>
                <Link className="text-btn" to="/bookings">
                  Расписание
                  <ArrowUpRight size={15} />
                </Link>
              </div>
              {!data.bookings.length ? (
                <Empty
                  title="Сегодня пока свободно"
                  text="Создайте первое занятие — инструктор увидит его в миниапе."
                />
              ) : (
                data.bookings.slice(0, 8).map((b) => (
                  <div className="dashboard-lesson" key={b.id}>
                    <div className="small" style={{ minWidth: 48 }}>
                      <strong>{b.start_at}</strong>
                      <p className="muted" style={{ marginTop: 5 }}>
                        {b.end_at}
                      </p>
                    </div>
                    <Avatar name={b.client.full_name} />
                    <Link className="grow" to={'/clients/' + b.client.id}>
                      <h3>{b.client.full_name}</h3>
                      <p className="small muted" style={{ marginTop: 5 }}>
                        {contextLabel(b.context)} · {b.instructor?.full_name}
                      </p>
                    </Link>
                    <Status value={b.status} />
                  </div>
                ))
              )}
            </section>
            <div className="stack">
              <section className="card">
                <div className="row between" style={{ marginBottom: 20 }}>
                  <h2>В фокусе внимания</h2>
                  <FlagIcon size={18} color="var(--amber)" />
                </div>
                {!data.flags.length ? (
                  <Empty
                    title="Нет активных флагов"
                    text="Система сообщит, если заметит повторяющиеся трудности."
                  />
                ) : (
                  data.flags.slice(0, 5).map((f) => (
                    <Link key={f.id} to={'/clients/' + f.client_id} className="focus-item">
                      <span className="badge amber">
                        <FlagIcon size={15} />
                      </span>
                      <div>
                        <h3>{f.client_name}</h3>
                        <p className="small muted" style={{ marginTop: 6 }}>
                          {f.reason}
                        </p>
                      </div>
                      <ArrowUpRight size={14} />
                    </Link>
                  ))
                )}
              </section>
              <section className="school-summary">
                <Activity size={24} />
                <h2>Практика в цифрах</h2>
                <div className="row between">
                  <div>
                    <strong>{data.stats.total_clients}</strong>
                    <p>учеников</p>
                  </div>
                  <div>
                    <strong>{data.stats.active_instructors}</strong>
                    <p>инструкторов</p>
                  </div>
                  <div>
                    <strong>{data.stats.no_show_today}</strong>
                    <p>неявок сегодня</p>
                  </div>
                </div>
              </section>
            </div>
          </div>
          {data.pending.length > 0 && (
            <section className="card">
              <div className="row between">
                <h2>Незавершённые отчёты</h2>
                <Link className="text-btn" to="/bookings">
                  Открыть доступ
                  <ArrowUpRight size={14} />
                </Link>
              </div>
              <p className="small muted" style={{ margin: '10px 0 18px' }}>
                Время доступа истекло. Уточните результат занятия и откройте инструктору повторный
                доступ.
              </p>
              {data.pending.slice(0, 5).map((b) => (
                <div className="row directory-item" key={b.id}>
                  <Avatar name={b.client.full_name} />
                  <div className="grow">
                    <h3>{b.client.full_name}</h3>
                    <p className="small muted">
                      {dateLabel(b.date)} · {b.instructor?.full_name}
                    </p>
                  </div>
                  <Status value={b.status} />
                </div>
              ))}
            </section>
          )}
        </>
      )}
    </div>
  )
}
