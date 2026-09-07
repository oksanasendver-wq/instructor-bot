import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Plus, PenLine, Trash2, ArrowUpRight, Check } from 'lucide-react'
import { adminApi } from '../services/api'
import { Avatar, Empty, ErrorBox, Loading, Modal, SearchField, useResource } from '../components/UI'
import { Person } from '../../../shared/types'
import { errorMessage } from '../../../shared/errors'
export function PeoplePage({ kind }: { kind: 'clients' | 'instructors' }) {
  const isInstructor = kind === 'instructors'
  const [archived, setArchived] = useState(false)
  const [search, setSearch] = useState('')
  const [editing, setEditing] = useState<Person | true | null>(null)
  const [deleting, setDeleting] = useState<Person | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const {
    data,
    error: loadError,
    loading,
    reload,
  } = useResource(
    () => adminApi.get<Person[]>('/' + kind + (!isInstructor && archived ? '?archived=true' : '')),
    kind + archived,
  )
  const people = data?.filter((p) =>
    (p.full_name + ' ' + p.phone).toLowerCase().includes(search.toLowerCase()),
  )
  return (
    <div className="stack">
      <div className="admin-heading">
        <div>
          <p className="eyebrow">{isInstructor ? 'Команда школы' : 'Учебные профили'}</p>
          <h1>
            {isInstructor ? 'Инструкторы' : 'Ученики'}{' '}
            <span className="muted">{data?.length ?? ''}</span>
          </h1>
          <p className="muted small">
            {isInstructor
              ? 'Команда, доступ в Telegram и назначенные занятия.'
              : 'Контакты, история обучения и понятный прогресс каждого ученика.'}
          </p>
        </div>
        <button className="btn" onClick={() => setEditing(true)}>
          <Plus size={17} />
          {isInstructor ? 'Добавить инструктора' : 'Добавить ученика'}
        </button>
      </div>
      <div className="table-tools">
        <SearchField value={search} onChange={setSearch} />
        <>
          {!isInstructor && (
            <button className="btn secondary" onClick={() => setArchived(!archived)}>
              {archived ? 'Активные ученики' : 'Архив учеников'}
            </button>
          )}
        </>
        <span className="small muted">
          {people ? people.length + ' записей' : 'Данные не загружены'}
        </span>
      </div>
      <ErrorBox message={error || loadError} retry={reload} />
      {loading && !data ? (
        <Loading />
      ) : people ? (
        <div className="card table-card">
          {!people?.length ? (
            <Empty
              title={
                search
                  ? 'Ничего не найдено'
                  : isInstructor
                    ? 'Соберите команду'
                    : 'Добавьте первого ученика'
              }
              text={
                search
                  ? 'Измените имя или номер в поиске.'
                  : 'Создайте карточку, затем назначьте занятие в расписании.'
              }
            >
              <button className="btn secondary" onClick={() => setEditing(true)}>
                <Plus size={16} />
                Добавить
              </button>
            </Empty>
          ) : (
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>{isInstructor ? 'Инструктор' : 'Ученик'}</th>
                    <th>Телефон</th>
                    <th>{isInstructor ? 'Telegram / КПП' : 'Учебная карточка'}</th>
                    <th>{isInstructor ? 'Статус' : 'Заметка школы'}</th>
                    <th>Действия</th>
                  </tr>
                </thead>
                <tbody>
                  {people.map((p) => (
                    <tr key={p.id}>
                      <td>
                        <div className="row">
                          <Avatar name={p.full_name} />
                          <div>
                            <strong>{p.full_name}</strong>
                            <p className="small muted">ID {p.id}</p>
                          </div>
                        </div>
                      </td>
                      <td>
                        <a href={'tel:' + p.phone}>{p.phone}</a>
                      </td>
                      <td>
                        {isInstructor ? (
                          <div>
                            <span className={'badge ' + (p.telegram_user_id ? 'green' : 'amber')}>
                              {p.telegram_user_id ? 'Привязан' : 'Ожидает входа'}
                            </span>
                            <p className="small muted" style={{ marginTop: 5 }}>
                              {p.transmission || 'Обе КПП'}
                            </p>
                          </div>
                        ) : (
                          <Link className="text-btn" to={'/clients/' + p.id}>
                            Открыть профиль <ArrowUpRight size={14} />
                          </Link>
                        )}
                      </td>
                      <td>
                        {isInstructor ? (
                          <span className={'badge ' + (p.is_active ? 'green' : '')}>
                            {p.is_active ? 'Активен' : 'Архив'}
                          </span>
                        ) : (
                          <span className="small muted">{p.notes_internal || '—'}</span>
                        )}
                      </td>
                      <td>
                        <div className="row">
                          <button
                            className="icon-btn"
                            aria-label={'Изменить ' + p.full_name}
                            onClick={() => setEditing(p)}
                          >
                            <PenLine size={15} />
                          </button>
                          <>
                            {archived && !isInstructor ? (
                              <button
                                className="text-btn"
                                onClick={async () => {
                                  try {
                                    await adminApi.post('/clients/' + p.id + '/restore', {})
                                    reload()
                                  } catch (e) {
                                    setError(errorMessage(e))
                                  }
                                }}
                              >
                                Восстановить
                              </button>
                            ) : (
                              <button
                                className="icon-btn"
                                aria-label={
                                  (isInstructor ? 'Архивировать ' : 'Удалить ') + p.full_name
                                }
                                onClick={() => setDeleting(p)}
                              >
                                <Trash2 size={15} />
                              </button>
                            )}
                          </>
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
          title={
            typeof editing === 'object'
              ? 'Изменить карточку'
              : isInstructor
                ? 'Новый инструктор'
                : 'Новый ученик'
          }
          onClose={() => setEditing(null)}
        >
          <PersonForm
            key={typeof editing === 'object' ? editing.id : 'new'}
            person={typeof editing === 'object' ? editing : undefined}
            instructor={isInstructor}
            onSave={async (value) => {
              if (typeof editing === 'object')
                await adminApi.patch('/' + kind + '/' + editing.id, value)
              else await adminApi.post('/' + kind, value)
              setEditing(null)
              reload()
            }}
          />
        </Modal>
      )}
      {deleting && (
        <Modal
          title={isInstructor ? 'Перенести инструктора в архив?' : 'Удалить карточку ученика?'}
          onClose={() => setDeleting(null)}
        >
          <p className="small muted">
            {deleting.full_name}.{' '}
            {isInstructor
              ? 'Вход в миниап будет отключён. История занятий сохранится, а инструктора можно будет активировать снова.'
              : 'Если у ученика уже есть отчёты, карточка перейдёт в архив, чтобы сохранить учебную историю.'}
          </p>
          <button
            className="btn danger full"
            disabled={busy}
            onClick={async () => {
              setBusy(true)
              try {
                await adminApi.remove('/' + kind + '/' + deleting.id)
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
            {busy ? 'Сохраняем…' : isInstructor ? 'В архив' : 'Удалить'}
          </button>
        </Modal>
      )}
    </div>
  )
}
function PersonForm({
  person,
  instructor,
  onSave,
}: {
  person?: Person
  instructor: boolean
  onSave: (value: object) => Promise<void>
}) {
  const [name, setName] = useState(person?.full_name || '')
  const [phone, setPhone] = useState(person?.phone || '')
  const [transmission, setTransmission] = useState(person?.transmission || '')
  const [notes, setNotes] = useState(person?.notes_internal || '')
  const [active, setActive] = useState(person?.is_active ?? true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  return (
    <form
      className="stack"
      onSubmit={async (e) => {
        e.preventDefault()
        setBusy(true)
        setError('')
        try {
          await onSave({
            full_name: name.trim(),
            phone,
            ...(instructor
              ? {
                  transmission: transmission || null,
                  is_active: active,
                  telegram_user_id: person?.telegram_user_id || null,
                }
              : { notes_internal: notes || null }),
          })
        } catch (e) {
          setError(errorMessage(e))
        } finally {
          setBusy(false)
        }
      }}
    >
      <label className="field">
        Имя и фамилия *
        <input
          autoFocus
          required
          minLength={2}
          maxLength={255}
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Например, Мария Сидорова"
        />
      </label>
      <label className="field">
        Телефон *
        <input
          type="tel"
          required
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
          placeholder="+7 700 123 45 67"
          maxLength={30}
        />
      </label>
      {instructor ? (
        <>
          <p className="small muted">
            При первом входе инструктор подтвердит этот номер в Telegram. Привязка произойдёт
            автоматически.
          </p>
          <label className="field">
            Коробка передач
            <select value={transmission} onChange={(e) => setTransmission(e.target.value)}>
              <option value="">Обе КПП</option>
              <option>МКПП</option>
              <option>АКПП</option>
            </select>
          </label>
          <label className="row small">
            <input
              type="checkbox"
              checked={active}
              onChange={(e) => setActive(e.target.checked)}
              style={{ width: 20, height: 20 }}
            />
            Активный инструктор
          </label>
        </>
      ) : (
        <label className="field">
          Внутренняя заметка
          <textarea
            maxLength={3000}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Информация для администратора"
          />
        </label>
      )}
      <ErrorBox message={error} />
      <button className="btn full" disabled={busy}>
        <Check size={17} />
        {busy ? 'Сохраняем…' : 'Сохранить карточку'}
      </button>
    </form>
  )
}
