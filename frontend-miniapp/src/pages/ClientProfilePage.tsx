import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { AlertTriangle, ArrowLeft, Car, ChevronRight, Phone } from 'lucide-react'
import { api } from '../services/api'
import { Avatar, Empty, ErrorBox, Loading, ScoreCard, Status, useResource } from '../components/UI'
import { contextLabel, dateLabel } from '../../../shared/types'
import type { HistoryItem } from '../../../shared/types'
import { ScoreTrend } from '../../../shared/ScoreTrendChart'
import { schoolDate } from '../../../shared/scoreTrend'

function LessonRows({ items }: { items: HistoryItem[] }) {
  return (
    <div className="grouped-card-container">
      {items.map((item, index) => (
        <Link
          key={item.booking_id}
          to={'/lessons/' + item.booking_id}
          className={
            'history-lesson-row profile-history-link ' +
            (index === items.length - 1 ? 'is-last' : '')
          }
        >
          <div className="history-lesson-icon">
            <Car size={20} />
          </div>
          <div className="history-lesson-info">
            <div className="history-lesson-title">
              {dateLabel(item.date)}, {item.start_at}
            </div>
            <div className="history-lesson-subtitle">
              {contextLabel(item.context)} · {item.instructor}
            </div>
            {item.overall_grade == null && <Status value={item.status} />}
          </div>
          <div className="history-lesson-score-box">
            {item.overall_grade != null && (
              <span
                className={
                  'history-score-badge ' + (item.overall_grade >= 4 ? 'score-high' : 'score-mid')
                }
              >
                {item.overall_grade}/5
              </span>
            )}
            <ChevronRight size={18} className="history-chevron" />
          </div>
        </Link>
      ))}
    </div>
  )
}

export default function ClientProfilePage() {
  const { clientId } = useParams()
  const [activeTab, setActiveTab] = useState('overview')
  const [lessonFilter, setLessonFilter] = useState('all')
  const [lessonLimit, setLessonLimit] = useState('10')
  const {
    data: profile,
    error,
    loading,
    reload,
  } = useResource(() => api.getClientProfile(Number(clientId)), clientId, true)
  const header = (
    <div className="ios-page-head">
      <Link to="/clients" className="ios-back-link" aria-label="К списку учеников">
        <ArrowLeft size={20} />
      </Link>
      <h1 className="ios-page-title">Профиль ученика</h1>
    </div>
  )
  if (loading && !profile)
    return (
      <div className="directory-page-container">
        {header}
        <Loading />
      </div>
    )
  if (error)
    return (
      <div className="directory-page-container">
        {header}
        <ErrorBox message={error} retry={reload} />
      </div>
    )
  if (!profile) return null

  const { client, scores, history, flags, stats } = profile
  const pastLessons = history.filter(
    (item) =>
      item.report_id != null ||
      ['completed', 'no_show', 'admin_review_required'].includes(item.status),
  )
  const filteredHistory = history.filter(
    (item) =>
      lessonFilter === 'all' ||
      item.context === (lessonFilter === 'city' ? 'Город' : 'Учебная площадка'),
  )
  const visibleHistory =
    lessonLimit === 'all' ? filteredHistory : filteredHistory.slice(0, Number(lessonLimit))
  const tabs = [
    ['overview', 'Обзор'],
    ['lessons', 'Занятия'],
    ['skills', 'Навыки'],
    ['flags', 'Флаги'],
    ['conclusions', 'Заключения'],
  ]

  return (
    <div className="directory-page-container">
      {header}
      <div className="directory-content-stack">
        <section className="client-hero-card">
          <Avatar name={client.full_name} large />
          <div className="client-hero-details">
            <h2 className="client-hero-name">{client.full_name}</h2>
            {client.phone && (
              <a href={'tel:' + client.phone} className="client-hero-phone">
                <Phone size={13} style={{ marginRight: 4 }} />
                <span>{client.phone}</span>
              </a>
            )}
          </div>
        </section>
        <nav className="ios-pill-tabs-bar" role="tablist" aria-label="Разделы профиля ученика">
          {tabs.map(([value, label]) => (
            <button
              key={value}
              role="tab"
              aria-selected={activeTab === value}
              className={'pill-tab-item ' + (activeTab === value ? 'is-active' : '')}
              onClick={() => setActiveTab(value)}
            >
              {label}
              {value === 'flags' && flags.some((flag) => flag.active)
                ? ` (${flags.filter((flag) => flag.active).length})`
                : ''}
            </button>
          ))}
        </nav>

        {activeTab === 'overview' && (
          <div className="tab-pane-stack">
            <ScoreCard scores={scores} />
            <section className="card profile-facts" aria-label="Учебная практика">
              <div>
                <strong>{stats.total_lessons}</strong>
                <span>Завершено занятий</span>
              </div>
              <div>
                <strong>{stats.total_hours ?? '—'}</strong>
                <span>Часов практики</span>
              </div>
              <div>
                <strong>{stats.no_show}</strong>
                <span>Неявок</span>
              </div>
            </section>
            <ScoreTrend
              history={profile.score_history}
              timezone={profile.timezone}
              today={
                profile.server_now
                  ? schoolDate(profile.server_now, profile.timezone || 'Asia/Almaty')
                  : undefined
              }
            />
            <section className="home-section-header" style={{ marginTop: 8 }}>
              <h2 className="home-section-title">Последние занятия</h2>
              <button
                type="button"
                className="home-section-all-link"
                onClick={() => setActiveTab('lessons')}
              >
                Все
              </button>
            </section>
            {pastLessons.length ? (
              <LessonRows items={pastLessons.slice(0, 3)} />
            ) : (
              <div className="card">
                <Empty
                  title="Занятий ещё не было"
                  text="Здесь появятся занятия и отчёты инструкторов."
                />
              </div>
            )}
          </div>
        )}

        {activeTab === 'lessons' && (
          <div className="tab-pane-stack">
            <div className="history-filters-bar">
              <select
                aria-label="Тип занятий"
                className="history-filter-select"
                value={lessonFilter}
                onChange={(e) => setLessonFilter(e.target.value)}
              >
                <option value="all">Все типы</option>
                <option value="city">Город</option>
                <option value="ground">Площадка</option>
              </select>
              <select
                aria-label="Количество занятий"
                className="history-filter-select"
                value={lessonLimit}
                onChange={(e) => setLessonLimit(e.target.value)}
              >
                <option value="10">Последние 10</option>
                <option value="20">Последние 20</option>
                <option value="all">Все занятия</option>
              </select>
            </div>
            {visibleHistory.length ? (
              <LessonRows items={visibleHistory} />
            ) : (
              <div className="card">
                <Empty title="Нет занятий" text="Занятия с выбранными параметрами не найдены." />
              </div>
            )}
          </div>
        )}

        {activeTab === 'skills' && (
          <div className="tab-pane-stack">
            <section className="card">
              <h2>Оценки навыков</h2>
              <p className="small muted" style={{ marginTop: 8 }}>
                Уровень рассчитан по выставленным оценкам. Неотработанные навыки не считаются
                нулевыми; оценки каждого занятия доступны в его отчёте.
              </p>
              {(
                [
                  ['ground', 'Площадка'],
                  ['city', 'Город'],
                ] as const
              ).map(([key, label]) => (
                <div className="profile-skill-context" key={key}>
                  <h3>{label}</h3>
                  {!scores[key].details.skills?.length ? (
                    <p className="small muted" style={{ marginTop: 10 }}>
                      Навыки пока не оценены.
                    </p>
                  ) : (
                    scores[key].details.skills!.map((skill) => (
                      <div className="profile-skill-row" key={skill.id}>
                        <div className="row between">
                          <span className="small">{skill.name}</span>
                          <strong className="small">{Math.round(skill.level)}%</strong>
                        </div>
                        <div className="progress-track">
                          <span style={{ width: skill.level + '%' }} />
                        </div>
                        <p className="small muted">
                          Последние оценки, начиная с новой: {skill.values.join(', ')} из 4.
                        </p>
                      </div>
                    ))
                  )}
                </div>
              ))}
            </section>
          </div>
        )}

        {activeTab === 'flags' && (
          <div className="tab-pane-stack">
            {!flags.length ? (
              <div className="card">
                <Empty
                  title="Флагов внимания нет"
                  text="Здесь будут отмечены трудности, выявленные по отчётам инструкторов."
                />
              </div>
            ) : (
              flags.map((flag) => (
                <article className="flag-card-item" key={flag.id}>
                  <div className="row between">
                    <span className="small muted">{contextLabel(flag.context)}</span>
                    <span className="badge-pill-flag">{flag.active ? 'Активен' : 'Закрыт'}</span>
                  </div>
                  <div className={'flag-banner-box ' + (!flag.active ? 'flag-banner-closed' : '')}>
                    <div className="flag-banner-icon">
                      <AlertTriangle size={18} />
                    </div>
                    <div className="flag-banner-content">
                      <h3 className="flag-banner-reason">{flag.reason}</h3>
                      <p className="flag-banner-meta">Создан: {dateLabel(flag.opened_at)}</p>
                      {flag.closed_at && (
                        <p className="flag-banner-meta">Закрыт: {dateLabel(flag.closed_at)}</p>
                      )}
                      {flag.closed_reason && (
                        <p className="flag-banner-meta">{flag.closed_reason}</p>
                      )}
                    </div>
                  </div>
                </article>
              ))
            )}
          </div>
        )}

        {activeTab === 'conclusions' && (
          <div className="tab-pane-stack">
            {!profile.conclusions.length ? (
              <div className="card">
                <Empty
                  title="Заключение ещё не оформлено"
                  text="Заключение школы появится после анализа обучения и утверждения администратором."
                />
              </div>
            ) : (
              profile.conclusions.map((conclusion) => (
                <article className="card stack" key={conclusion.id}>
                  <span className="eyebrow">
                    Версия {conclusion.version} · {dateLabel(conclusion.created_at)}
                  </span>
                  <h3>{conclusion.status}</h3>
                  {conclusion.approved_by_type && (
                    <p className="small muted">
                      Утвердил:{' '}
                      {conclusion.approved_by_name ||
                        (conclusion.approved_by_type === 'admin'
                          ? 'администратор школы'
                          : `инструктор №${conclusion.approved_by_id}`)}
                    </p>
                  )}
                  <p style={{ whiteSpace: 'pre-wrap', fontSize: 13, lineHeight: 1.8 }}>
                    {conclusion.text}
                  </p>
                </article>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  )
}
