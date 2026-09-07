import { Link, useParams } from 'react-router-dom'
import { AlertTriangle, ArrowRight, Pencil } from 'lucide-react'
import { api } from '../services/api'
import { Avatar, Empty, ErrorBox, Loading, Status, useResource } from '../components/UI'
import { contextLabel, dateLabel } from '../../../shared/types'
import { PageHead } from './DirectoryPages'

export default function LessonPage() {
  const { bookingId } = useParams()
  const { data, error, loading, reload } = useResource(
    async () => {
      const booking = await api.getBooking(Number(bookingId))
      const report = booking.report_id ? await api.getReport(booking.report_id) : null
      return { booking, report }
    },
    bookingId,
    true,
  )
  const booking = data?.booking
  const report = data?.report
  const interventions = report?.interventions ?? (report ? [report.intervention] : [])

  return (
    <div className="directory-page-container">
      <PageHead title="Занятие" backTo={booking ? '/client/' + booking.client.id : '/reports'} />
      <div className="directory-content-stack">
        <ErrorBox message={error} retry={reload} />
        {loading && !data ? (
          <Loading />
        ) : (
          booking && (
            <>
              <section className="aux-card">
                <Link to={'/client/' + booking.client.id} className="aux-person-link">
                  <Avatar name={booking.client.full_name} />
                  <div>
                    <h2>{booking.client.full_name}</h2>
                    <span className="aux-note">Открыть профиль ученика</span>
                  </div>
                  <ArrowRight size={18} />
                </Link>
                <dl className="aux-facts">
                  <div>
                    <dt>Дата</dt>
                    <dd>
                      {dateLabel(booking.date, { day: 'numeric', month: 'long', year: 'numeric' })}
                    </dd>
                  </div>
                  <div>
                    <dt>Время школы</dt>
                    <dd>
                      {booking.start_at} – {booking.end_at}
                    </dd>
                  </div>
                  <div>
                    <dt>Длительность</dt>
                    <dd>{booking.duration_minutes} мин</dd>
                  </div>
                  <div>
                    <dt>Практика</dt>
                    <dd>
                      {contextLabel(booking.context)}
                      {booking.transmission ? ' · ' + booking.transmission : ''}
                    </dd>
                  </div>
                  {booking.instructor && (
                    <div>
                      <dt>Инструктор</dt>
                      <dd>{booking.instructor.full_name}</dd>
                    </div>
                  )}
                  <div>
                    <dt>Статус</dt>
                    <dd>
                      <Status value={booking.status} />
                    </dd>
                  </div>
                </dl>
                {booking.admin_comment && (
                  <p className="aux-report-note">{booking.admin_comment}</p>
                )}
              </section>
              {!report ? (
                <section className="aux-card">
                  <Empty
                    title="Отчёт ещё не заполнен"
                    text="После завершения занятия здесь будут доступны оценки навыков, упражнения и комментарий инструктора."
                  />
                  {booking.actions.includes('report') && (
                    <Link
                      to={'/report/' + booking.id}
                      className="btn-submit-primary aux-link-button"
                    >
                      Заполнить отчёт
                    </Link>
                  )}
                </section>
              ) : (
                <>
                  <section className="aux-card">
                    <h2>Оценки инструктора</h2>
                    <dl className="aux-facts">
                      <div>
                        <dt>Общая оценка занятия</dt>
                        <dd>{report.overall_grade_1_5} / 5</dd>
                      </div>
                      <div>
                        <dt>Самостоятельность</dt>
                        <dd>{report.autonomy_level}</dd>
                      </div>
                      {report.quick_verdict && (
                        <div>
                          <dt>Вердикт по занятию</dt>
                          <dd>{report.quick_verdict}</dd>
                        </div>
                      )}
                    </dl>
                    {report.skills.length ? (
                      <div className="aux-skill-list">
                        {report.skills.map((skill) => (
                          <div className="aux-skill-row" key={skill.skill_id}>
                            <span>{skill.name || `Навык №${skill.skill_id}`}</span>
                            <strong>{skill.value} / 4</strong>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="aux-note">Оценки навыков отсутствуют.</p>
                    )}
                    <p className="aux-note">
                      Показаны оценки, сохранённые в этом отчёте. Неоценённые навыки не добавляются.
                    </p>
                  </section>
                  <section className="aux-card">
                    <h2>Что отрабатывали</h2>
                    {report.exercises.length ? (
                      <ul className="aux-exercises">
                        {report.exercises.map((exercise) => (
                          <li key={exercise.exercise_id}>
                            {exercise.name || `Упражнение №${exercise.exercise_id}`}
                            {exercise.section && (
                              <span className="aux-note"> · {exercise.section}</span>
                            )}
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="aux-note">Упражнения не указаны.</p>
                    )}
                  </section>
                  <section className="aux-card">
                    <h2>Вмешательства и безопасность</h2>
                    {interventions.length ? (
                      interventions.map((event, index) => (
                        <div
                          key={index}
                          className={
                            event.is_critical ? 'aux-event aux-event-critical' : 'aux-event'
                          }
                        >
                          <strong>
                            {event.is_critical && <AlertTriangle size={16} />}{' '}
                            {event.type === 'нет' ? 'Вмешательство не требовалось' : event.type}
                          </strong>
                          {event.is_critical && <p>Критическое событие</p>}
                          {event.reason && <p>{event.reason}</p>}
                          {event.description && (
                            <p className="aux-report-note">{event.description}</p>
                          )}
                        </div>
                      ))
                    ) : (
                      <p className="aux-note">Данные о вмешательствах отсутствуют.</p>
                    )}
                  </section>
                  <section className="aux-card">
                    <h2>Комментарий инструктора</h2>
                    <p className="aux-report-note">
                      {report.comment_internal || 'Комментарий не добавлен.'}
                    </p>
                  </section>
                  <section className="aux-card">
                    <h2>История отчёта</h2>
                    <dl className="aux-facts">
                      {report.created_at && (
                        <div>
                          <dt>Сохранён</dt>
                          <dd>
                            {dateLabel(report.created_at, {
                              day: 'numeric',
                              month: 'long',
                              year: 'numeric',
                            })}
                          </dd>
                        </div>
                      )}
                      {report.last_edited_at && (
                        <div>
                          <dt>Исправлен</dt>
                          <dd>
                            {dateLabel(report.last_edited_at, {
                              day: 'numeric',
                              month: 'long',
                              year: 'numeric',
                            })}
                          </dd>
                        </div>
                      )}
                      {report.formula_version && (
                        <div>
                          <dt>Версия методики</dt>
                          <dd>{report.formula_version}</dd>
                        </div>
                      )}
                    </dl>
                    {report.can_edit && booking.can_edit_report ? (
                      <Link
                        to={'/report/' + booking.id + '?edit=' + report.id}
                        className="btn-draft-secondary aux-link-button"
                      >
                        <Pencil size={16} /> Исправить отчёт
                      </Link>
                    ) : (
                      <p className="aux-note">
                        Отчёт доступен для просмотра. Для исправления обратитесь к администратору
                        школы.
                      </p>
                    )}
                  </section>
                </>
              )}
            </>
          )
        )}
      </div>
    </div>
  )
}
