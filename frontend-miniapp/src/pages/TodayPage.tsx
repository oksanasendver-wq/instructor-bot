import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { CheckCheck, ChevronLeft, ChevronRight, RefreshCw } from 'lucide-react'
import { api } from '../services/api'
import { useInstructor } from '../App'
import { Empty, ErrorBox, Loading, useResource, Modal } from '../components/UI'
import { Booking, contextLabel, dateLabel, money, statusLabels } from '../../../shared/types'
import { errorMessage } from '../../../shared/errors'

export default function TodayPage({ schedule = false }: { schedule?: boolean }) {
  const instructor = useInstructor()
  const navigate = useNavigate()
  const [selected, setSelected] = useState(instructor.today)
  const [busy, setBusy] = useState<number | null>(null)
  const [actionError, setActionError] = useState('')
  const [confirm, setConfirm] = useState<Booking | null>(null)

  const resource = useResource(
    async () => {
      const [bookings, clients, flags] = await Promise.all([
        api.getBookings(schedule ? { today_only: false } : { on_date: selected }),
        api.getClients(),
        api.getFlags(),
      ])
      return { bookings, clients, flags }
    },
    selected + schedule,
    true,
  )
  const { data, error, loading, reload } = resource

  const act = async (booking: Booking, action: string) => {
    setBusy(booking.id)
    setActionError('')
    try {
      if (action === 'arrived') await api.markArrived(booking.id)
      if (action === 'no-show') await api.markNoShow(booking.id)
      if (action === 'finish') {
        await api.finishBooking(booking.id)
        navigate('/report/' + booking.id)
        return
      }
      if (action === 'report') {
        navigate('/report/' + booking.id)
        return
      }
      if (action === 'payment') await api.payment(booking.id, true)
      window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('success')
      setConfirm(null)
      reload()
    } catch (e) {
      setActionError(errorMessage(e))
      setConfirm(null)
      reload()
    } finally {
      setBusy(null)
    }
  }

  const base = new Date(selected + 'T12:00:00')
  const weekday = (base.getDay() + 6) % 7
  const days = Array.from({ length: 7 }, (_, i) => {
    const d = new Date(base)
    d.setDate(base.getDate() - weekday + i)
    return {
      value:
        d.getFullYear() +
        '-' +
        String(d.getMonth() + 1).padStart(2, '0') +
        '-' +
        String(d.getDate()).padStart(2, '0'),
      day: d.getDate(),
      label: ['пн', 'вт', 'ср', 'чт', 'пт', 'сб', 'вс'][i],
    }
  })

  const shift = (offset: number) => {
    const d = new Date(base)
    d.setDate(d.getDate() + offset)
    setSelected(
      d.getFullYear() +
        '-' +
        String(d.getMonth() + 1).padStart(2, '0') +
        '-' +
        String(d.getDate()).padStart(2, '0'),
    )
  }

  const hour = Number(
    new Intl.DateTimeFormat('ru-RU', {
      hour: 'numeric',
      hour12: false,
      timeZone: instructor.timezone,
    }).format(new Date()),
  )
  const greeting = hour < 12 ? 'Доброе утро' : hour < 18 ? 'Добрый день' : 'Добрый вечер'
  const firstName = instructor.full_name.split(' ')[0]
  const todayBookingsCount = data ? data.bookings.length : 0
  const activeFlagsCount = data ? data.flags.filter((f) => f.active).length : 0
  const activeClientsCount = data ? data.clients.length : 0

  return (
    <div className="main-page-container">
      {/* 1. Greeting Section (Screen 1 in mockup) */}
      {/* 1. Aurora Hero Card (Design 5) */}
      <section className="aurora-hero">
        <h1 className="aurora-hero-greeting">
          {schedule ? 'Всё по расписанию' : `${greeting},\n${firstName}! ✨`}
        </h1>
        <p className="aurora-hero-subtitle">
          {!data
            ? 'Загружаем расписание…'
            : schedule
              ? `Записей в расписании: ${todayBookingsCount}`
              : `Расписание на ${dateLabel(selected)}`}
        </p>

        {/* Aurora Stat Bubbles */}
        <div className="aurora-stat-bubbles">
          <div className="stat-bubble">
            <strong>{data ? todayBookingsCount : '—'}</strong>
            <span>{schedule ? 'Записей' : 'Занятий'}</span>
          </div>

          <Link to="/flags" className="stat-bubble stat-bubble-alert">
            <strong style={{ color: '#FFD1D9' }}>{data ? activeFlagsCount : '—'}</strong>
            <span>Риски</span>
          </Link>

          <Link to="/clients" className="stat-bubble">
            <strong>{data ? activeClientsCount : '—'}</strong>
            <span>Учеников</span>
          </Link>
        </div>
      </section>

      {/* Calendar Week Strip */}
      {!schedule && (
        <section className="home-calendar-strip">
          <div className="home-calendar-nav">
            <button
              className="calendar-shift-btn"
              onClick={() => shift(-7)}
              aria-label="Предыдущая неделя"
            >
              <ChevronLeft size={16} />
            </button>
            <span className="calendar-current-month">
              {dateLabel(selected, { month: 'long', year: 'numeric' })}
            </span>
            <button
              className="calendar-shift-btn"
              onClick={() => shift(7)}
              aria-label="Следующая неделя"
            >
              <ChevronRight size={16} />
            </button>
          </div>
          <div className="home-days-row">
            {days.map((d) => (
              <button
                key={d.value}
                onClick={() => setSelected(d.value)}
                className={
                  'home-day-btn ' +
                  (d.value === selected ? 'selected ' : '') +
                  (d.value === instructor.today ? 'is-today' : '')
                }
              >
                <span className="day-name">{d.label}</span>
                <span className="day-num">{d.day}</span>
              </button>
            ))}
          </div>
        </section>
      )}

      {/* 3. Lessons Section Header */}
      <section className="home-section-header">
        <h2 className="home-section-title">{schedule ? 'Все записи' : 'Ближайшие занятия'}</h2>
        <Link to={schedule ? '/' : '/schedule'} className="home-section-all-link">
          {schedule ? 'Сегодня' : 'Все'}
        </Link>
      </section>
      <Link to="/reports" className="home-section-all-link aux-history-link">
        История занятий и отчёты <ChevronRight size={14} />
      </Link>

      <ErrorBox message={error || actionError} retry={reload} />

      {/* 4. Lessons List (Screen 1 in mockup: Unified list of clean student rows) */}
      {loading && !data ? (
        <Loading />
      ) : !data?.bookings.length ? (
        <div className="card empty-lessons-card">
          <Empty
            title="В расписании свободно"
            text="Когда администратор назначит занятие, оно появится здесь автоматически."
          >
            <button className="btn secondary compact" onClick={reload}>
              <RefreshCw size={14} />
              Обновить
            </button>
          </Empty>
        </div>
      ) : (
        <div className="aurora-lessons-feed">
          {data.bookings.map((booking) => {
            const action = booking.actions?.find((a) =>
              ['arrived', 'finish', 'report', 'no-show'].includes(a),
            )

            return (
              <div
                key={booking.id}
                className={
                  'aurora-lesson-card ' + (booking.status === 'in_progress' ? 'is-live ' : '')
                }
                onClick={() => navigate('/lessons/' + booking.id)}
                role="link"
                tabIndex={0}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' && event.target === event.currentTarget)
                    navigate('/lessons/' + booking.id)
                }}
              >
                {/* Left: Avatar */}
                <div className="aurora-avatar">
                  {booking.client.full_name
                    .split(' ')
                    .map((w) => w[0])
                    .join('')
                    .slice(0, 2)}
                </div>

                {/* Center: Info */}
                <div className="aurora-card-info">
                  <div className="aurora-card-name">{booking.client.full_name}</div>
                  <div className="aurora-card-sub">
                    {schedule && dateLabel(booking.date) + ' · '}
                    {booking.start_at} – {booking.end_at} · {contextLabel(booking.context)}
                  </div>
                  {booking.amount_due > 0 && booking.payment_status === 'pending' && (
                    <div className="lesson-pending-payment">
                      К получению: {money(booking.amount_due)}
                    </div>
                  )}
                </div>

                {/* Right: Action Button + Chevron */}
                <div className="lesson-action-col">
                  {action ? (
                    <button
                      className={
                        action === 'no-show' ? 'lesson-action-btn btn-no-show' : 'aurora-btn-pill'
                      }
                      disabled={busy === booking.id}
                      onClick={(e) => {
                        e.stopPropagation()
                        action === 'no-show' ? setConfirm(booking) : act(booking, action)
                      }}
                    >
                      {busy === booking.id
                        ? '...'
                        : (
                            {
                              arrived: 'Пришёл',
                              finish: 'Завершить',
                              report: 'Оценить',
                              'no-show': 'Не пришёл',
                            } as Record<string, string>
                          )[action]}
                    </button>
                  ) : booking.status === 'completed' ? (
                    <span className="lesson-completed-icon" title="Завершено">
                      <CheckCheck size={20} />
                    </span>
                  ) : (
                    <span className="lesson-status-tag">
                      {statusLabels[booking.status] || booking.status}
                    </span>
                  )}

                  <span className="arrow-icon-subtle">›</span>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Confirmation Modal for No-Show */}
      {confirm && (
        <Modal title="Отметить неявку?" onClose={() => setConfirm(null)}>
          <p className="small muted">
            {confirm.client.full_name} · {confirm.start_at}–{confirm.end_at}. Неявка сохранится в
            истории посещений и не повлияет на оценку навыков.
          </p>
          <button
            className="btn danger full"
            disabled={busy !== null}
            onClick={() => act(confirm, 'no-show')}
          >
            Подтвердить неявку
          </button>
          <button className="btn ghost full" onClick={() => setConfirm(null)}>
            Отмена
          </button>
        </Modal>
      )}
    </div>
  )
}
