import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  AlertTriangle,
  ArrowLeft,
  ChevronRight,
  Clock3,
  HelpCircle,
  Info,
  LogOut,
  Route,
  ShieldCheck,
  TrendingUp,
} from 'lucide-react'
import { api } from '../services/api'
import { useInstructor } from '../App'
import { Avatar, Empty, ErrorBox, Loading, SearchField, useResource } from '../components/UI'
import { dateLabel, contextLabel } from '../../../shared/types'

export function PageHead({ title, backTo = '/' }: { title: string; backTo?: string }) {
  return (
    <div className="ios-page-head">
      <Link to={backTo} className="ios-back-link" aria-label="Назад">
        <ArrowLeft size={20} />
      </Link>
      <h1 className="ios-page-title">{title}</h1>
    </div>
  )
}

export function ClientsPage() {
  const [search, setSearch] = useState('')
  const { data, error, loading, reload } = useResource(api.getClients, '', true)
  const clients = data?.filter((c) =>
    (c.full_name + ' ' + c.phone).toLowerCase().includes(search.toLowerCase()),
  )

  return (
    <div className="directory-page-container">
      <PageHead title="Ученики" />
      <div className="directory-content-stack">
        <SearchField
          value={search}
          onChange={setSearch}
          placeholder="Поиск по имени или телефону"
        />
        <ErrorBox message={error} retry={reload} />
        {loading && !data ? (
          <Loading />
        ) : (
          <div className="grouped-card-container">
            {!clients?.length ? (
              <Empty
                title={search ? 'Никого не нашли' : 'Пока нет учеников'}
                text={
                  search
                    ? 'Попробуйте другое имя или номер телефона.'
                    : 'Ученики появятся, когда администратор назначит вам занятия.'
                }
              />
            ) : (
              clients.map((c, idx) => (
                <Link
                  key={c.id}
                  to={'/client/' + c.id}
                  className={'grouped-row-item ' + (idx === clients.length - 1 ? 'is-last' : '')}
                >
                  <Avatar name={c.full_name} />
                  <div className="grouped-item-info">
                    <div className="grouped-item-title">{c.full_name}</div>
                    <div className="grouped-item-subtitle">{c.phone}</div>
                  </div>
                  {c.active_flags > 0 && (
                    <span className="badge-pill-flag">
                      <AlertTriangle size={12} />
                      <span>{c.active_flags}</span>
                    </span>
                  )}
                  <ChevronRight size={18} className="grouped-item-chevron" />
                </Link>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export function FlagsPage() {
  const [active, setActive] = useState(true)
  const { data, error, loading, reload } = useResource(api.getFlags, '', true)
  const flags = data?.filter((f) => f.active === active)

  return (
    <div className="directory-page-container">
      <PageHead title="Флаги внимания" />
      <div className="directory-content-stack">
        {/* Segmented control (Screen 5 in mockup: [ Активные (2) ]  [ Закрытые ]) */}
        <div className="ios-segmented-control">
          <button
            className={'segmented-tab ' + (active ? 'selected' : '')}
            onClick={() => setActive(true)}
          >
            Активные {data ? `(${data.filter((f) => f.active).length})` : ''}
          </button>
          <button
            className={'segmented-tab ' + (!active ? 'selected' : '')}
            onClick={() => setActive(false)}
          >
            Закрытые
          </button>
        </div>

        <ErrorBox message={error} retry={reload} />

        {loading && !data ? (
          <Loading />
        ) : !flags?.length ? (
          <div className="card empty-lessons-card">
            <Empty
              title={active ? 'Нет активных флагов' : 'Нет закрытых флагов'}
              text="Флаги появляются при повторяющихся трудностях ученика и снимаются после прогресса."
            />
          </div>
        ) : (
          <div className="flags-list-stack">
            {flags.map((f) => (
              <Link key={f.id} to={'/client/' + f.client_id} className="flag-card-item">
                <div className="flag-student-row">
                  <Avatar name={f.client_name || 'Ученик'} />
                  <span className="flag-student-name">{f.client_name}</span>
                  <span className="grow" />
                  <ChevronRight size={18} className="flag-chevron" />
                </div>
                <div className={'flag-banner-box ' + (!f.active ? 'flag-banner-closed' : '')}>
                  <div className="flag-banner-icon">
                    <AlertTriangle size={18} />
                  </div>
                  <div className="flag-banner-content">
                    <div className="flag-banner-reason">{f.reason}</div>
                    <div className="flag-banner-meta">
                      {f.closed_reason ||
                        `${contextLabel(f.context)} · Создан: ${dateLabel(f.opened_at)}`}
                    </div>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export function ReportsPage() {
  const [filterType, setFilterType] = useState('all')
  const [filterCount, setFilterCount] = useState('10')
  const { data, error, loading, reload } = useResource(
    () => api.getBookings({ history: true }),
    '',
    true,
  )

  const filteredData = data
    ?.filter((b) => {
      if (filterType === 'city') return b.context.toLowerCase().includes('город')
      if (filterType === 'ground') return b.context.toLowerCase().includes('площадка')
      return true
    })
    .slice(0, filterCount === 'all' ? undefined : Number(filterCount))

  return (
    <div className="directory-page-container">
      <PageHead title="Занятия" />
      <div className="directory-content-stack">
        {/* Filters Bar: Screen 6 in mockup */}
        <div className="history-filters-bar">
          <select
            className="history-filter-select"
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
          >
            <option value="all">Все типы</option>
            <option value="city">Город</option>
            <option value="ground">Площадка</option>
          </select>

          <select
            className="history-filter-select"
            value={filterCount}
            onChange={(e) => setFilterCount(e.target.value)}
          >
            <option value="10">Последние 10</option>
            <option value="20">Последние 20</option>
            <option value="all">Все занятия</option>
          </select>
        </div>

        <ErrorBox message={error} retry={reload} />

        {loading && !data ? (
          <Loading />
        ) : !filteredData?.length ? (
          <div className="card empty-lessons-card">
            <Empty
              title="Занятия ещё впереди"
              text="После завершения первого занятия и оценки отчёт появится здесь."
            />
          </div>
        ) : (
          <div className="grouped-card-container">
            {filteredData.map((b, idx) => (
              <Link
                key={b.id}
                to={'/lessons/' + b.id}
                className={
                  'history-lesson-row ' + (idx === filteredData.length - 1 ? 'is-last' : '')
                }
              >
                <div className="history-lesson-icon">
                  <Route size={20} />
                </div>
                <div className="history-lesson-info">
                  <div className="history-lesson-title">
                    {dateLabel(b.date)}, {b.start_at}
                  </div>
                  <div className="history-lesson-subtitle">
                    {b.client.full_name} · {contextLabel(b.context)}
                  </div>
                </div>
                <div className="history-lesson-score-box">
                  <span className="history-score-badge">
                    {b.overall_grade !== null ? `${b.overall_grade}/5` : '—'}
                  </span>
                  <ChevronRight size={18} className="history-chevron" />
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export function AccountPage() {
  const i = useInstructor()
  const [help, setHelp] = useState(false)

  return (
    <div className="directory-page-container">
      <PageHead title="Профиль" />
      <div className="directory-content-stack">
        {/* Screen 8 in mockup: Big round avatar (76px) + Name + 'Инструктор' */}
        <section className="account-hero-card">
          <Avatar name={i.full_name} large />
          <h2 className="account-hero-name">{i.full_name}</h2>
          <p className="account-hero-role">
            Инструктор {i.transmission ? `· ${i.transmission}` : ''}
          </p>
        </section>

        {/* Grouped menu card */}
        <section className="grouped-card-container">
          <Link to="/account/statistics" className="grouped-row-item">
            <div className="menu-icon-square icon-blue">
              <TrendingUp size={19} />
            </div>
            <div className="grouped-item-info">
              <div className="grouped-item-title">Моя статистика</div>
              <div className="grouped-item-subtitle">Часы практики и занятия</div>
            </div>
            <ChevronRight size={18} className="grouped-item-chevron" />
          </Link>

          <div className="grouped-row-item">
            <div className="menu-icon-square icon-green">
              <ShieldCheck size={19} />
            </div>
            <div className="grouped-item-info">
              <div className="grouped-item-title">Доступ подтверждён</div>
              <div className="grouped-item-subtitle">{i.phone}</div>
            </div>
          </div>

          <Link to="/account/time" className="grouped-row-item">
            <div className="menu-icon-square icon-blue">
              <Clock3 size={19} />
            </div>
            <div className="grouped-item-info">
              <div className="grouped-item-title">Время школы</div>
              <div className="grouped-item-subtitle">{i.timezone}</div>
            </div>
            <ChevronRight size={18} className="grouped-item-chevron" />
          </Link>

          <button
            type="button"
            className="grouped-row-item aux-menu-button"
            onClick={() => setHelp(!help)}
            aria-expanded={help}
            aria-controls="account-help"
          >
            <div className="menu-icon-square icon-amber">
              <HelpCircle size={19} />
            </div>
            <div className="grouped-item-info">
              <div className="grouped-item-title">Помощь</div>
              <div className="grouped-item-subtitle">Как работать с приложением</div>
            </div>
            <ChevronRight size={18} className="grouped-item-chevron" />
          </button>

          {help && (
            <div className="account-help-note" id="account-help">
              Отметьте «Пришёл» перед занятием. После окончания нажмите «Завершить», выберите
              упражнения и выставьте оценки навыков. Отчёт сразу сохранится в истории школы.
            </div>
          )}

          <Link to="/account/about" className="grouped-row-item is-last">
            <div className="menu-icon-square icon-gray">
              <Info size={19} />
            </div>
            <div className="grouped-item-info">
              <div className="grouped-item-title">О приложении</div>
              <div className="grouped-item-subtitle">Профиль обучения и история оценок</div>
            </div>
            <ChevronRight size={18} className="grouped-item-chevron" />
          </Link>
        </section>

        {/* Screen 8: Soft red logout button */}
        <button
          className="ios-logout-btn"
          onClick={() => {
            localStorage.removeItem('instructor_token')
            window.dispatchEvent(new Event('instructor-logout'))
          }}
        >
          <LogOut size={18} />
          <span>Выйти</span>
        </button>
      </div>
    </div>
  )
}
