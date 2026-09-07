import { useState, useEffect, useRef, ReactNode } from 'react'
import {
  AlertCircle,
  ArrowUpRight,
  BookOpen,
  Check,
  ChevronRight,
  Flag as FlagIcon,
  Route,
  Search,
  ShieldCheck,
  TrendingUp,
  TrendingDown,
  X,
} from 'lucide-react'
import { Profile, Score, HistoryItem, dateLabel, contextLabel, statusLabels } from './types'
import { errorMessage } from './errors'
import { ScoreTrend } from './ScoreTrendChart'
import { schoolDate } from './scoreTrend'

export function useResource<T>(load: () => Promise<T>, key = '', poll = false) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [version, setVersion] = useState(0)
  const identity = useRef(key)
  const fn = useRef(load)
  fn.current = load
  useEffect(() => {
    let active = true
    if (identity.current !== key) {
      identity.current = key
      setData(null)
      setError('')
    }
    const run = async () => {
      try {
        const value = await fn.current()
        if (active) {
          setData(value)
          setError('')
        }
      } catch (e) {
        if (active) setError(errorMessage(e))
      } finally {
        if (active) setLoading(false)
      }
    }
    setLoading(true)
    run()
    const timer = poll ? window.setInterval(run, 30000) : undefined
    const focus = () => {
      if (document.visibilityState === 'visible') run()
    }
    if (poll) document.addEventListener('visibilitychange', focus)
    return () => {
      active = false
      clearInterval(timer)
      document.removeEventListener('visibilitychange', focus)
    }
  }, [key, version, poll])
  return {
    data: identity.current === key ? data : null,
    error: identity.current === key ? error : '',
    loading: identity.current !== key || loading,
    reload: () => setVersion((v) => v + 1),
  }
}
export function Avatar({ name, large = false }: { name: string; large?: boolean }) {
  return (
    <span className={'avatar' + (large ? ' large' : '')} data-color={name.length % 4}>
      {name
        .split(' ')
        .filter(Boolean)
        .slice(0, 2)
        .map((n) => n[0])
        .join('')}
    </span>
  )
}
export function ErrorBox({ message, retry }: { message: string; retry?: () => void }) {
  if (!message) return null
  return (
    <div className="alert" role="alert">
      <AlertCircle size={18} />
      <div className="grow">
        {message}
        {retry && (
          <button className="text-btn" onClick={retry}>
            Повторить попытку
          </button>
        )}
      </div>
    </div>
  )
}
export function Empty({
  title,
  text,
  children,
}: {
  title: string
  text: string
  children?: ReactNode
}) {
  return (
    <div className="empty">
      <div className="empty-icon">
        <Route size={27} />
      </div>
      <h3>{title}</h3>
      <p>{text}</p>
      {children}
    </div>
  )
}
export function Loading() {
  return (
    <div className="stack" aria-label="Загрузка" role="status">
      <div className="skeleton" />
      <div className="skeleton" />
      <div className="skeleton" />
    </div>
  )
}
export function Status({ value }: { value: string }) {
  const tone =
    (
      {
        completed: 'green',
        in_progress: 'blue',
        assessment_required: 'amber',
        no_show: 'red',
        admin_review_required: 'red',
        arrival_window: 'blue',
      } as Record<string, string>
    )[value] || ''
  return (
    <span className={'badge ' + tone}>
      <span className="dot" />
      {statusLabels[value] || value}
    </span>
  )
}
export function SearchField({
  value,
  onChange,
  placeholder = 'Найти по имени или телефону',
}: {
  value: string
  onChange: (v: string) => void
  placeholder?: string
}) {
  return (
    <label className="search">
      <Search size={18} />
      <input
        type="search"
        aria-label={placeholder}
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </label>
  )
}
export function ScoreRing({ score }: { score: number | null }) {
  const color =
    score === null
      ? 'var(--muted)'
      : score >= 75
        ? 'var(--green)'
        : score >= 50
          ? 'var(--blue)'
          : 'var(--amber)'
  return (
    <div
      className="score-ring"
      role="img"
      aria-label={score === null ? 'Недостаточно данных для оценки' : Math.round(score) + ' из 100'}
    >
      <svg viewBox="0 0 128 128">
        <circle cx="64" cy="64" r="56" stroke="var(--line)" />
        <circle
          cx="64"
          cy="64"
          r="56"
          stroke={color}
          strokeDasharray={Math.max(0, Math.min(100, score || 0)) * 3.5186 + ' 351.86'}
          strokeLinecap="round"
        />
      </svg>
      <div className="ring-value">
        <strong>{score === null ? '—' : Math.round(score)}</strong>
        <span>{score === null ? 'нет данных' : 'из 100'}</span>
      </div>
    </div>
  )
}
export function ScoreCard({ scores }: { scores: { ground: Score; city: Score; overall: Score } }) {
  const overall = scores.overall
  return (
    <section className="card">
      <div className="row between">
        <h2>Оценка вождения</h2>
        <ShieldCheck size={19} color="var(--green)" />
      </div>
      <div className="score-main">
        <ScoreRing score={overall.score} />
        <div className="grow" style={{ minWidth: 0 }}>
          <p className="eyebrow">Общая готовность</p>
          <h3 style={{ margin: '8px 0' }}>
            {overall.score === null ? 'Оценка формируется' : overall.status}
          </h3>
          <p className="small muted">
            {overall.score === null
              ? 'Нужны достоверные оценки площадки и города.'
              : 'По данным учебных отчётов.'}
          </p>
          {overall.score != null && overall.delta != null && (
            <span
              className={'badge ' + (overall.delta < 0 ? 'amber' : 'green')}
              style={{ marginTop: 10, whiteSpace: 'normal', lineHeight: 1.5 }}
            >
              {overall.delta < 0 ? <TrendingDown size={12} /> : <TrendingUp size={12} />}
              {overall.delta > 0 ? '+' : ''}
              {Math.round(overall.delta)} к предыдущему занятию
            </span>
          )}
        </div>
      </div>
      <div className="metric-grid">
        {(
          [
            ['ground', 'Площадка'],
            ['city', 'Город'],
            ['overall', 'Готовность'],
          ] as const
        ).map(([key, label]) => (
          <div className="score-tile" key={key}>
            <strong>{scores[key].score === null ? '—' : Math.round(scores[key].score!)}</strong>
            <span>{label}</span>
            <small className="profile-score-status">{scores[key].status}</small>
          </div>
        ))}
      </div>
      <p className="small muted" style={{ marginTop: 14 }}>
        Площадка: {scores.ground.status.toLowerCase()} · Город: {scores.city.status.toLowerCase()}
      </p>
      <details className="profile-score-explanation">
        <summary>Основания оценки</summary>
        {(
          [
            ['ground', 'Площадка'],
            ['city', 'Город'],
            ['overall', 'Общая готовность'],
          ] as const
        ).map(([key, label]) => {
          const score = scores[key]
          return (
            <div key={key}>
              <p>
                <strong>{label}</strong> · {score.status}
                {score.formula_version != null && ` · Методика v${score.formula_version}`}
              </p>
              {typeof score.details.lessons_count === 'number' && (
                <p>Учтено занятий: {score.details.lessons_count}</p>
              )}
              {typeof score.details.skill_coverage === 'number' && (
                <p>Повторно оценено основных навыков: {score.details.skill_coverage}%</p>
              )}
              {typeof score.details.autonomy_cap === 'number' && (
                <p>Ограничение по самостоятельности: {score.details.autonomy_cap}</p>
              )}
              {typeof score.details.safety_cap === 'number' && (
                <p>Ограничение по безопасности: {score.details.safety_cap}</p>
              )}
              {typeof score.details.formula === 'string' && <p>{score.details.formula}</p>}
            </div>
          )
        })}
      </details>
    </section>
  )
}
export function HistoryList({
  items,
  onEdit,
  onOpen,
}: {
  items: HistoryItem[]
  onEdit?: (item: HistoryItem) => void
  onOpen?: (item: HistoryItem) => void
}) {
  if (!items.length)
    return (
      <Empty
        title="История начинается с первого урока"
        text="После занятия здесь появятся упражнения, оценки и комментарии инструктора."
      />
    )
  return (
    <div>
      {items.map((item) => (
        <div className="history-row" key={item.booking_id}>
          <div className="row">
            <span
              className={'badge ' + (item.context === 'Город' ? 'blue' : 'amber')}
              style={{ padding: 10 }}
            >
              <Route size={19} />
            </span>
            <div className="grow">
              <h3>
                {dateLabel(item.date)} · {item.start_at}
              </h3>
              <p className="small muted" style={{ marginTop: 5 }}>
                {contextLabel(item.context)} · {item.instructor}
              </p>
            </div>
            {item.overall_grade ? (
              <span className={'grade ' + (item.overall_grade < 3 ? 'low' : '')}>
                {item.overall_grade}
                <small style={{ fontSize: 9 }}>/5</small>
              </span>
            ) : (
              <Status value={item.status} />
            )}
          </div>
          {item.quick_verdict && (
            <p className="small" style={{ marginTop: 12 }}>
              {item.quick_verdict}
            </p>
          )}
          {item.comment_internal && <p className="note">{item.comment_internal}</p>}
          {!!item.exercises?.length && (
            <p className="small muted" style={{ marginTop: 10 }}>
              {item.exercises.map((e) => e.name).join(' · ')}
            </p>
          )}
          {item.critical && (
            <div className="badge red" style={{ marginTop: 10 }}>
              <AlertCircle size={12} />
              Критическое событие
            </div>
          )}
          {item.interventions
            ?.filter((i) => i.type !== 'нет')
            .map((i, idx) => (
              <p className="small muted" key={idx}>
                {i.type}: {i.reason || i.description}
              </p>
            ))}
          {onOpen && (
            <button className="text-btn" onClick={() => onOpen(item)}>
              Открыть занятие <ChevronRight size={14} />
            </button>
          )}
          {onEdit && item.report_id && (
            <button className="text-btn" onClick={() => onEdit(item)}>
              Исправить отчёт <ChevronRight size={14} />
            </button>
          )}
        </div>
      ))}
    </div>
  )
}
export function ProfilePanel({
  profile,
  onEdit,
  onOpen,
  extra,
}: {
  profile: Profile
  onEdit?: (item: HistoryItem) => void
  onOpen?: (item: HistoryItem) => void
  extra?: ReactNode
}) {
  const [tab, setTab] = useState('overview')
  const tabs = [
    ['overview', 'Обзор'],
    ['history', 'Занятия'],
    ['skills', 'Навыки'],
    ['flags', 'Внимание'],
    ['conclusions', 'Заключения'],
  ]
  const skills = [
    ...(profile.scores.ground.details.skills || []),
    ...(profile.scores.city.details.skills || []),
  ]
  return (
    <div className="stack">
      <div className="row" style={{ padding: '6px 0' }}>
        <Avatar name={profile.client.full_name} large />
        <div className="grow">
          <h2 style={{ fontSize: 23 }}>{profile.client.full_name}</h2>
          <a className="small muted" href={'tel:' + profile.client.phone}>
            {profile.client.phone}
          </a>
          <div style={{ marginTop: 8 }}>
            <span className="badge blue">Ученик · ID {profile.client.id}</span>
          </div>
        </div>
      </div>
      <div className="tabs" role="tablist">
        {tabs.map(([id, label]) => (
          <button
            role="tab"
            aria-selected={tab === id}
            className={tab === id ? 'active' : ''}
            key={id}
            onClick={() => setTab(id)}
          >
            {label}
            {id === 'flags' && profile.flags.some((f) => f.active)
              ? ' · ' + profile.flags.filter((f) => f.active).length
              : ''}
          </button>
        ))}
      </div>
      {tab === 'overview' && (
        <>
          <ScoreCard scores={profile.scores} />
          {profile.flags.some((f) => f.active) && (
            <button
              className="alert"
              onClick={() => setTab('flags')}
              style={{ border: 0, textAlign: 'left' }}
            >
              <FlagIcon size={18} />
              <div className="grow">{profile.flags.find((f) => f.active)?.reason}</div>
              <ChevronRight size={16} />
            </button>
          )}
          <div className="metric-grid">
            <div className="metric">
              <BookOpen size={17} color="var(--blue)" />
              <strong>{profile.stats.total_lessons}</strong>
              <span>занятий завершено</span>
            </div>
            <div className="metric">
              <Route size={17} color="var(--amber)" />
              <strong>{profile.stats.total_hours ?? '—'}</strong>
              <span>часов практики</span>
            </div>
            <div className="metric">
              <Check size={17} color="var(--green)" />
              <strong>{profile.stats.no_show}</strong>
              <span>неявок</span>
            </div>
          </div>
          <ScoreTrend
            history={profile.score_history}
            timezone={profile.timezone}
            today={
              profile.server_now
                ? schoolDate(profile.server_now, profile.timezone || 'Asia/Almaty')
                : undefined
            }
          />
          <div className="section-heading">
            <h2>Последние занятия</h2>
            <button className="text-btn" onClick={() => setTab('history')}>
              Все <ArrowUpRight size={14} />
            </button>
          </div>
          <div className="card">
            <HistoryList
              items={profile.history.filter((h) => h.status === 'completed').slice(0, 3)}
              onEdit={onEdit}
              onOpen={onOpen}
            />
          </div>
        </>
      )}
      {tab === 'history' && (
        <section className="card">
          <HistoryList items={profile.history} onEdit={onEdit} onOpen={onOpen} />
        </section>
      )}
      {tab === 'skills' && (
        <div className="card stack">
          <h2>Текущий уровень навыков</h2>
          <p className="small muted">
            Уровень по фактически выставленным оценкам. Пропущенные навыки не считаются нулём.
          </p>
          {!skills.length && (
            <Empty title="Навыки ещё не оценены" text="Оценки появятся после первого отчёта." />
          )}
          {skills.map((s, i) => (
            <div key={i}>
              <div className="row between" style={{ marginBottom: 9 }}>
                <span className="small">{s.name}</span>
                <strong className="small">{Math.round(s.level)}%</strong>
              </div>
              <div className="progress-track">
                <span style={{ width: s.level + '%' }} />
              </div>
            </div>
          ))}
        </div>
      )}
      {tab === 'flags' && (
        <div className="stack">
          {!profile.flags.length && (
            <div className="card">
              <Empty
                title="Всё под наблюдением"
                text="Повторяющиеся трудности будут отмечены здесь автоматически."
              />
            </div>
          )}
          {profile.flags.map((f) => (
            <div className="card stack" key={f.id}>
              <div className="row between">
                <span className={'badge ' + (f.active ? 'red' : 'green')}>
                  {f.active ? 'Требует внимания' : 'Закрыт'}
                </span>
                <span className="small muted">{contextLabel(f.context)}</span>
              </div>
              <h3>{f.reason}</h3>
              <p className="small muted">
                Открыт {dateLabel(f.opened_at)}
                {f.closed_reason ? ' · ' + f.closed_reason : ''}
              </p>
            </div>
          ))}
        </div>
      )}
      {tab === 'conclusions' && (
        <div className="stack">
          {!profile.conclusions.length && (
            <div className="card">
              <Empty
                title="Заключение ещё не оформлено"
                text="Администратор оформляет его после анализа занятий, навыков и безопасности."
              />
            </div>
          )}
          {profile.conclusions.map((c) => (
            <article className="card stack" key={c.id}>
              <span className="eyebrow">
                Версия {c.version} · {dateLabel(c.created_at)}
              </span>
              <h3>{c.status}</h3>
              {c.approved_by_type && (
                <p className="small muted">
                  Утвердил:{' '}
                  {c.approved_by_name ||
                    (c.approved_by_type === 'admin'
                      ? 'администратор школы'
                      : `инструктор №${c.approved_by_id}`)}
                </p>
              )}
              <p style={{ whiteSpace: 'pre-wrap', fontSize: 13, lineHeight: 1.8 }}>{c.text}</p>
            </article>
          ))}
        </div>
      )}
      {extra}
    </div>
  )
}
export function Modal({
  title,
  onClose,
  children,
}: {
  title: string
  onClose: () => void
  children: ReactNode
}) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const previous = document.activeElement as HTMLElement
    const overflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    const elements = () =>
      Array.from(
        ref.current?.querySelectorAll<HTMLElement>(
          'button:not(:disabled),input,select,textarea,a[href],[tabindex="0"]',
        ) || [],
      )
    elements()[0]?.focus()
    const key = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
      if (event.key === 'Tab') {
        const all = elements()
        const first = all[0]
        const last = all[all.length - 1]
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault()
          last?.focus()
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault()
          first?.focus()
        }
      }
    }
    document.addEventListener('keydown', key)
    return () => {
      document.body.style.overflow = overflow
      document.removeEventListener('keydown', key)
      previous?.focus()
    }
  }, [onClose])
  return (
    <div
      className="modal-backdrop"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <div className="modal stack" role="dialog" aria-modal="true" aria-label={title} ref={ref}>
        <div className="row between">
          <h2>{title}</h2>
          <button className="icon-btn" onClick={onClose} aria-label="Закрыть">
            <X size={18} />
          </button>
        </div>
        {children}
      </div>
    </div>
  )
}
