import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight, Clock3, RefreshCw } from 'lucide-react'
import { api } from '../services/api'
import { Empty, ErrorBox, Loading, useResource } from '../components/UI'
import { PageHead } from './DirectoryPages'

const number = (value: number) =>
  new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 2 }).format(value)

export function StatisticsPage() {
  const { data, loading, error, reload } = useResource(api.getStatistics, '', true)
  return (
    <div className="directory-page-container">
      <PageHead title="Моя статистика" backTo="/account" />
      <div className="directory-content-stack">
        <ErrorBox message={error} retry={reload} />
        {loading && !data ? (
          <Loading />
        ) : (
          data && (
            <>
              <p className="aux-note">
                Ваши занятия за всё время. Часы практики рассчитаны по длительности проведённых
                занятий.
              </p>
              <section className="aux-stat-grid">
                {(
                  [
                    ['Проведено занятий', data.total_lessons],
                    ['Часов практики', data.total_hours],
                    ['Учеников на занятиях', data.total_clients],
                    ['Отчётов сохранено', data.reported_lessons],
                  ] as const
                ).map(([label, value]) => (
                  <div className="aux-stat-card" key={label}>
                    <strong>{number(value)}</strong>
                    <span>{label}</span>
                  </div>
                ))}
              </section>
              <section className="aux-card">
                <h2>Практика и отчётность</h2>
                <dl className="aux-facts">
                  <div>
                    <dt>Площадка</dt>
                    <dd>{number(data.ground_lessons)}</dd>
                  </div>
                  <div>
                    <dt>Город</dt>
                    <dd>{number(data.city_lessons)}</dd>
                  </div>
                  <div>
                    <dt>Ожидают отчёта</dt>
                    <dd>{number(data.pending_reports)}</dd>
                  </div>
                  <div>
                    <dt>Неявки</dt>
                    <dd>{number(data.no_show)}</dd>
                  </div>
                  <div>
                    <dt>Средняя оценка занятий</dt>
                    <dd>
                      {data.average_grade === null
                        ? 'Нет оценок'
                        : `${number(data.average_grade)} / 5`}
                    </dd>
                  </div>
                </dl>
              </section>
              {data.total_lessons === 0 && (
                <Empty
                  title="Практика ещё впереди"
                  text="Статистика начнёт накапливаться после проведения занятий."
                />
              )}
              <Link to="/reports" className="btn-submit-primary aux-link-button">
                История занятий <ArrowRight size={17} />
              </Link>
            </>
          )
        )}
      </div>
    </div>
  )
}

export function SchoolTimePage() {
  const [tick, setTick] = useState(() => performance.now())
  const { data, loading, error, reload } = useResource(
    async () => {
      const profile = await api.getMe()
      return { profile, receivedAt: performance.now() }
    },
    '',
    true,
  )
  useEffect(() => {
    const timer = window.setInterval(() => setTick(performance.now()), 1000)
    return () => window.clearInterval(timer)
  }, [])
  const serverTimestamp = data ? new Date(data.profile.school_time).getTime() : NaN
  const schoolNow =
    data && Number.isFinite(serverTimestamp)
      ? new Date(serverTimestamp + Math.max(0, tick - data.receivedAt))
      : null
  return (
    <div className="directory-page-container">
      <PageHead title="Время школы" backTo="/account" />
      <div className="directory-content-stack">
        <ErrorBox message={error} retry={reload} />
        {loading && !data ? (
          <Loading />
        ) : (
          data && (
            <>
              <section className="aux-card aux-clock-card">
                <Clock3 size={28} />
                {schoolNow ? (
                  <>
                    <time className="aux-clock" dateTime={schoolNow.toISOString()}>
                      {new Intl.DateTimeFormat('ru-RU', {
                        timeZone: data.profile.timezone,
                        hour: '2-digit',
                        minute: '2-digit',
                        second: '2-digit',
                        hourCycle: 'h23',
                      }).format(schoolNow)}
                    </time>
                    <p>
                      {new Intl.DateTimeFormat('ru-RU', {
                        timeZone: data.profile.timezone,
                        weekday: 'long',
                        day: 'numeric',
                        month: 'long',
                        year: 'numeric',
                      }).format(schoolNow)}
                    </p>
                  </>
                ) : (
                  <p>Сервер не передал текущее время.</p>
                )}
                <span className="aux-note">{data.profile.timezone}</span>
              </section>
              <section className="aux-card">
                <h2>Как читать расписание</h2>
                <p>
                  Время начала и окончания занятий указано в часовом поясе школы. Часы телефона и
                  ваше местоположение не меняют время в расписании.
                </p>
                <p className="aux-note">
                  Часы синхронизируются с сервером при открытии страницы и обновлении данных.
                </p>
              </section>
              <button
                type="button"
                className="btn-draft-secondary aux-link-button"
                onClick={reload}
                disabled={loading}
              >
                <RefreshCw size={16} /> Обновить время
              </button>
              <Link to="/schedule" className="btn-submit-primary aux-link-button">
                Открыть расписание <ArrowRight size={17} />
              </Link>
            </>
          )
        )}
      </div>
    </div>
  )
}

export function AboutPage() {
  const { data, loading, error, reload } = useResource(api.getMe)
  return (
    <div className="directory-page-container">
      <PageHead title="О приложении" backTo="/account" />
      <div className="directory-content-stack">
        <ErrorBox message={error} retry={reload} />
        <section className="aux-card">
          <h2>Рабочее место инструктора</h2>
          <p>
            Расписание, посещаемость и отчёты о практике собираются в постоянный профиль обучения
            ученика. История помогает инструктору продолжить обучение с учётом предыдущих занятий.
          </p>
          <p>
            Оценка вождения рассчитывается по сохранённым наблюдениям, самостоятельности и
            вмешательствам. Если данных недостаточно, числовая оценка не показывается.
          </p>
          <p>
            Результаты доступны сотрудникам школы в рамках их доступа. Школа оформляет заключения по
            накопленной истории обучения в админке.
          </p>
        </section>
        {loading && !data ? (
          <Loading />
        ) : (
          data && (
            <section className="aux-card">
              <h2>Информация о системе</h2>
              <dl className="aux-facts">
                <div>
                  <dt>Система</dt>
                  <dd>{data.app_name || 'Название не указано'}</dd>
                </div>
                <div>
                  <dt>Версия сервера</dt>
                  <dd>{data.app_version || 'Не указана'}</dd>
                </div>
                <div>
                  <dt>Часовой пояс</dt>
                  <dd>{data.timezone}</dd>
                </div>
              </dl>
            </section>
          )
        )}
        <section className="aux-card">
          <h2>Поддержка</h2>
          <p>
            По вопросам расписания, доступа и исправления закрытого отчёта обратитесь к
            администратору школы. В обращении укажите дату занятия и имя ученика.
          </p>
        </section>
        <Link to="/reports" className="btn-draft-secondary aux-link-button">
          Просмотреть отчёты <ArrowRight size={17} />
        </Link>
      </div>
    </div>
  )
}
