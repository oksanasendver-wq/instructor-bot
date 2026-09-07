import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Plus, PenLine, Trash2, CalendarDays, KeyRound } from 'lucide-react'
import { adminApi } from '../services/api'
import { Avatar, Empty, ErrorBox, Loading, Modal, Status, useResource } from '../components/UI'
import { Booking, Person, dateLabel, contextLabel, money } from '../../../shared/types'
import { errorMessage } from '../../../shared/errors'
export default function BookingsPage() {
  const [date, setDate] = useState('')
  const [status, setStatus] = useState('')
  const [editing, setEditing] = useState<Booking | true | null>(null)
  const [deleting, setDeleting] = useState<Booking | null>(null)
  const [grant, setGrant] = useState<Booking | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const {
    data,
    error: loadError,
    loading,
    reload,
  } = useResource(
    () =>
      adminApi.get<{ bookings: Booking[] }>('/bookings', {
        ...(date ? { date_from: date, date_to: date } : {}),
        ...(status ? { status_filter: status } : {}),
      }),
    date + status,
    true,
  )
  return (
    <div className="stack">
      <div className="admin-heading">
        <div>
          <p className="eyebrow">Практика каждый день</p>
          <h1>Расписание</h1>
          <p className="small muted">Назначайте занятия и следите за посещаемостью.</p>
        </div>
        <button className="btn" onClick={() => setEditing(true)}>
          <Plus size={17} />
          Создать занятие
        </button>
      </div>
      <div className="table-tools">
        <div className="row wrap">
          <label className="field">
            <span className="small muted">Дата</span>
            <input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
          </label>
          <label className="field">
            <span className="small muted">Статус</span>
            <select value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="">Все занятия</option>
              <option value="planned">Запланированы</option>
              <option value="arrival_window">Ожидаем прихода</option>
              <option value="in_progress">Идут сейчас</option>
              <option value="assessment_required">Нужна оценка</option>
              <option value="admin_review_required">Нужен разбор</option>
              <option value="completed">Завершены</option>
              <option value="no_show">Неявки</option>
            </select>
          </label>
          {(date || status) && (
            <button
              className="text-btn"
              onClick={() => {
                setDate('')
                setStatus('')
              }}
            >
              Сбросить
            </button>
          )}
        </div>
        <span className="small muted">
          {data ? data.bookings.length + ' занятий' : 'Данные не загружены'}
        </span>
      </div>
      <ErrorBox message={error || loadError} retry={reload} />
      {loading && !data ? (
        <Loading />
      ) : data ? (
        <div className="card table-card">
          {!data?.bookings.length ? (
            <Empty
              title="Здесь появятся занятия"
              text="Выберите ученика, инструктора и время. Запись появится в миниапе инструктора."
            >
              <button className="btn secondary" onClick={() => setEditing(true)}>
                Создать занятие
              </button>
            </Empty>
          ) : (
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Дата и время</th>
                    <th>Ученик / инструктор</th>
                    <th>Практика</th>
                    <th>Статус</th>
                    <th>Оплата</th>
                    <th>Действия</th>
                  </tr>
                </thead>
                <tbody>
                  {data.bookings.map((b) => (
                    <tr key={b.id}>
                      <td>
                        <strong>{dateLabel(b.date)}</strong>
                        <p className="small muted" style={{ marginTop: 6 }}>
                          {b.start_at} — {b.end_at}
                        </p>
                      </td>
                      <td>
                        <Link to={'/clients/' + b.client.id} className="row">
                          <Avatar name={b.client.full_name} />
                          <div>
                            <strong>{b.client.full_name}</strong>
                            <p className="small muted" style={{ marginTop: 5 }}>
                              {b.instructor?.full_name}
                            </p>
                          </div>
                        </Link>
                      </td>
                      <td>
                        <span className={'badge ' + (b.context === 'Город' ? 'blue' : 'amber')}>
                          {contextLabel(b.context)}
                        </span>
                        <p className="small muted" style={{ marginTop: 6 }}>
                          {b.transmission} · {b.duration_minutes} мин
                        </p>
                      </td>
                      <td>
                        <Status value={b.status} />
                        {b.overall_grade && (
                          <p className="small" style={{ marginTop: 7 }}>
                            Оценка {b.overall_grade}/5
                          </p>
                        )}
                      </td>
                      <td>
                        <strong>{money(b.amount_due)}</strong>
                        <p className="small muted" style={{ marginTop: 5 }}>
                          {b.payment_status === 'received'
                            ? 'Получено'
                            : b.amount_due > 0
                              ? 'К получению'
                              : b.payment_type}
                        </p>
                      </td>
                      <td>
                        <div className="row">
                          {['planned', 'arrival_window'].includes(b.status) && (
                            <button
                              className="icon-btn"
                              onClick={() => setEditing(b)}
                              aria-label={'Изменить занятие ' + b.id}
                            >
                              <PenLine size={15} />
                            </button>
                          )}
                          {['assessment_required', 'admin_review_required', 'completed'].includes(
                            b.status,
                          ) && (
                            <button
                              className="icon-btn"
                              onClick={() => setGrant(b)}
                              aria-label={'Открыть доступ к занятию ' + b.id}
                            >
                              <KeyRound size={15} />
                            </button>
                          )}
                          {['planned', 'arrival_window', 'no_show'].includes(b.status) && (
                            <button
                              className="icon-btn"
                              onClick={() => setDeleting(b)}
                              aria-label={'Удалить занятие ' + b.id}
                            >
                              <Trash2 size={15} />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      ) : null}
      {editing && (
        <Modal
          title={typeof editing === 'object' ? 'Изменить занятие' : 'Новое занятие'}
          onClose={() => setEditing(null)}
        >
          <BookingForm
            booking={typeof editing === 'object' ? editing : undefined}
            onSaved={() => {
              setEditing(null)
              reload()
            }}
          />
        </Modal>
      )}
      {deleting && (
        <Modal title="Удалить занятие?" onClose={() => setDeleting(null)}>
          <p className="small muted">
            {deleting.client.full_name} · {dateLabel(deleting.date)} · {deleting.start_at}. Запись
            исчезнет из расписания инструктора.
          </p>
          <button
            className="btn danger"
            disabled={busy}
            onClick={async () => {
              setBusy(true)
              try {
                await adminApi.remove('/bookings/' + deleting.id)
                setDeleting(null)
                reload()
              } catch (e) {
                setError(errorMessage(e))
                setDeleting(null)
              } finally {
                setBusy(false)
              }
            }}
          >
            Удалить занятие
          </button>
        </Modal>
      )}
      {grant && (
        <Modal title="Открыть доступ инструктору" onClose={() => setGrant(null)}>
          <GrantForm
            booking={grant}
            onSaved={() => {
              setGrant(null)
              reload()
            }}
          />
        </Modal>
      )}
    </div>
  )
}
function BookingForm({ booking, onSaved }: { booking?: Booking; onSaved: () => void }) {
  const { data, error, loading } = useResource(async () => {
    const [clients, instructors, stats] = await Promise.all([
      adminApi.get<Person[]>('/clients'),
      adminApi.get<Person[]>('/instructors'),
      adminApi.get<{ today: string }>('/stats'),
    ])
    return { clients, instructors: instructors.filter((i) => i.is_active), today: stats.today }
  })
  const [form, setForm] = useState({
    client_id: String(booking?.client.id || ''),
    instructor_id: String(booking?.instructor?.id || ''),
    date: booking?.date || '',
    start_at: booking?.start_at || '10:00',
    duration_minutes: booking?.duration_minutes || 60,
    context: booking?.context || 'Учебная площадка',
    transmission: booking?.transmission || 'АКПП',
    payment_type: booking?.payment_type || 'уже оплачено',
    amount_due: booking?.amount_due || 0,
    admin_comment: booking?.admin_comment || '',
  })
  const [busy, setBusy] = useState(false)
  const [saveError, setSaveError] = useState('')
  const update = (key: string, value: string | number) => setForm((f) => ({ ...f, [key]: value }))
  if (loading) return <Loading />
  if (error) return <ErrorBox message={error} />
  if (!data?.clients.length || !data.instructors.length)
    return (
      <Empty
        title="Сначала добавьте участников"
        text="Для занятия нужны ученик и активный инструктор."
      >
        <Link className="btn secondary" to={!data?.clients.length ? '/clients' : '/instructors'}>
          Открыть карточки
        </Link>
      </Empty>
    )
  return (
    <form
      className="stack"
      onSubmit={async (e) => {
        e.preventDefault()
        setBusy(true)
        setSaveError('')
        try {
          const payload = {
            ...form,
            client_id: Number(form.client_id),
            instructor_id: Number(form.instructor_id),
            date: form.date || data.today,
          }
          if (booking) await adminApi.patch('/bookings/' + booking.id, payload)
          else await adminApi.post('/bookings', payload)
          onSaved()
        } catch (e) {
          setSaveError(errorMessage(e))
        } finally {
          setBusy(false)
        }
      }}
    >
      <div className="form-grid">
        <label className="field">
          Ученик *
          <select
            required
            value={form.client_id}
            onChange={(e) => update('client_id', e.target.value)}
          >
            <option value="">Выберите ученика</option>
            {data.clients.map((c) => (
              <option key={c.id} value={c.id}>
                {c.full_name} · {c.phone}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          Инструктор *
          <select
            required
            value={form.instructor_id}
            onChange={(e) => {
              update('instructor_id', e.target.value)
              const selected = data.instructors.find((i) => i.id === Number(e.target.value))
              if (selected?.transmission) update('transmission', selected.transmission)
            }}
          >
            <option value="">Выберите инструктора</option>
            {data.instructors.map((i) => (
              <option key={i.id} value={i.id}>
                {i.full_name}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          Дата *
          <input
            required
            type="date"
            value={form.date || data.today}
            onChange={(e) => update('date', e.target.value)}
          />
        </label>
        <label className="field">
          Начало *
          <input
            required
            type="time"
            value={form.start_at}
            onChange={(e) => update('start_at', e.target.value)}
          />
        </label>
        <label className="field">
          Длительность, мин *
          <input
            required
            type="number"
            min={15}
            max={240}
            step={15}
            value={form.duration_minutes}
            onChange={(e) => update('duration_minutes', Number(e.target.value))}
          />
        </label>
        <label className="field">
          Контекст
          <select value={form.context} onChange={(e) => update('context', e.target.value)}>
            <option>Учебная площадка</option>
            <option>Город</option>
          </select>
        </label>
        <label className="field">
          КПП
          <select
            value={form.transmission}
            onChange={(e) => update('transmission', e.target.value)}
          >
            <option>АКПП</option>
            <option>МКПП</option>
          </select>
        </label>
        <label className="field">
          Источник оплаты
          <select
            value={form.payment_type}
            onChange={(e) => {
              update('payment_type', e.target.value)
              if (!['наличные', 'другое'].includes(e.target.value)) update('amount_due', 0)
            }}
          >
            {['уже оплачено', 'наличные', 'пакет', 'сертификат', 'другое'].map((v) => (
              <option key={v}>{v}</option>
            ))}
          </select>
        </label>
        <label className="field">
          К получению, ₸
          <input
            required
            type="number"
            min={0}
            max={99999999}
            disabled={!['наличные', 'другое'].includes(form.payment_type)}
            value={form.amount_due}
            onChange={(e) => update('amount_due', Number(e.target.value))}
          />
        </label>
        <label className="field wide">
          Комментарий администратора
          <textarea
            maxLength={3000}
            value={form.admin_comment}
            onChange={(e) => update('admin_comment', e.target.value)}
            placeholder="Место встречи или другая важная информация"
          />
        </label>
      </div>
      <ErrorBox message={saveError} />
      <button className="btn full" disabled={busy}>
        <CalendarDays size={17} />
        {busy ? 'Сохраняем…' : 'Сохранить занятие'}
      </button>
    </form>
  )
}
export function GrantForm({ booking, onSaved }: { booking: Booking; onSaved: () => void }) {
  const [minutes, setMinutes] = useState(30),
    [reason, setReason] = useState(''),
    [attended, setAttended] = useState(false),
    [busy, setBusy] = useState(false),
    [error, setError] = useState('')
  return (
    <form
      className="stack"
      onSubmit={async (e) => {
        e.preventDefault()
        setBusy(true)
        try {
          await adminApi.post('/access-grants', {
            booking_id: booking.id,
            minutes,
            reason,
            confirm_attended: attended,
          })
          onSaved()
        } catch (e) {
          setError(errorMessage(e))
        } finally {
          setBusy(false)
        }
      }}
    >
      <p className="small muted">
        {booking.client.full_name} · {dateLabel(booking.date)}. Доступ откроется только к этому
        ученику и выбранному занятию.
      </p>
      <label className="field">
        Срок доступа
        <select value={minutes} onChange={(e) => setMinutes(Number(e.target.value))}>
          {[15, 30, 60, 120].map((n) => (
            <option key={n} value={n}>
              {n} минут
            </option>
          ))}
        </select>
      </label>
      <label className="field">
        Причина *
        <textarea
          required
          minLength={3}
          maxLength={1000}
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="Почему нужно заполнить или исправить отчёт"
        />
      </label>
      {booking.status === 'admin_review_required' && (
        <label className="row small">
          <input
            type="checkbox"
            checked={attended}
            onChange={(e) => setAttended(e.target.checked)}
          />
          Подтверждаю, что занятие состоялось
        </label>
      )}
      <ErrorBox message={error} />
      <button className="btn full" disabled={busy}>
        <KeyRound size={16} />
        {busy ? 'Открываем…' : 'Открыть доступ'}
      </button>
    </form>
  )
}
