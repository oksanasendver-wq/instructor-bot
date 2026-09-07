import { useState, useRef } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  ArrowLeft,
  Printer,
  Sparkles,
  FileCheck,
  KeyRound,
  ShieldCheck,
  PenLine,
} from 'lucide-react'
import { adminApi } from '../services/api'
import {
  Empty,
  ErrorBox,
  Loading,
  Modal,
  ProfilePanel,
  Status,
  useResource,
} from '../components/UI'
import ReportEditor from '../components/ReportEditor'
import { GrantForm } from './BookingsPage'
import {
  Booking,
  CatalogItem,
  HistoryItem,
  Person,
  Profile,
  ReportInput,
  dateLabel,
} from '../../../shared/types'
import { errorMessage } from '../../../shared/errors'
interface Draft {
  id: number
  generated_text: string
  provider: string
  model: string
  created_at: string
}
export default function ClientPage() {
  const { id } = useParams()
  const [editing, setEditing] = useState<HistoryItem | null>(null)
  const [viewing, setViewing] = useState<HistoryItem | null>(null)
  const [grant, setGrant] = useState<Booking | null>(null)
  const [conclusion, setConclusion] = useState(false)
  const [booklet, setBooklet] = useState(false)
  const [draft, setDraft] = useState<Draft | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const {
    data,
    error: loadError,
    loading,
    reload,
  } = useResource(
    async () => {
      const [profile, bookings, drafts] = await Promise.all([
        adminApi.get<Profile>('/clients/' + id + '/profile'),
        adminApi.get<{ bookings: Booking[] }>('/bookings', { client_id: Number(id) }),
        adminApi.get<Draft[]>('/clients/' + id + '/ai-drafts'),
      ])
      return { profile, bookings: bookings.bookings, drafts }
    },
    id,
    true,
  )
  return (
    <div className="stack">
      <div className="admin-heading">
        <div className="row">
          <Link to="/clients" className="icon-btn" aria-label="К списку учеников">
            <ArrowLeft size={18} />
          </Link>
          <div>
            <p className="eyebrow">Учебная карточка</p>
            <h1>Прогресс ученика</h1>
          </div>
        </div>
        <div className="row wrap profile-actions">
          <button className="btn ghost" onClick={() => setBooklet(true)} disabled={!data}>
            <Printer size={16} />
            Для бумажной книжки
          </button>
          <button className="btn" disabled={!data} onClick={() => setConclusion(true)}>
            <FileCheck size={17} />
            Оформить заключение
          </button>
        </div>
      </div>
      <ErrorBox message={loadError || error} retry={reload} />
      {notice && <div className="alert success">{notice}</div>}
      {loading && !data ? (
        <Loading />
      ) : (
        data && (
          <div className="client-grid">
            <div>
              <ProfilePanel profile={data.profile} onOpen={setViewing} onEdit={setEditing} />
            </div>
            <aside className="stack">
              <section className="card stack">
                <div className="row between">
                  <h2>Заключение школы</h2>
                  <Sparkles size={19} color="var(--blue)" />
                </div>
                <p className="small muted">
                  ИИ поможет собрать историю в текст. Проверьте черновик и утвердите вывод от имени
                  школы.
                </p>
                <button
                  className="btn secondary full"
                  disabled={busy || !data.profile.stats.total_lessons}
                  onClick={async () => {
                    setBusy(true)
                    setError('')
                    try {
                      setDraft(await adminApi.post<Draft>('/clients/' + id + '/ai-draft'))
                      reload()
                    } catch (e) {
                      setError(errorMessage(e))
                    } finally {
                      setBusy(false)
                    }
                  }}
                >
                  <Sparkles size={16} />
                  {busy ? 'Готовим черновик…' : 'Сформировать ИИ-черновик'}
                </button>
                {data.drafts.map((d) => (
                  <button
                    className="text-btn"
                    style={{ textAlign: 'left' }}
                    key={d.id}
                    onClick={() => setDraft(d)}
                  >
                    Черновик от {dateLabel(d.created_at)}
                  </button>
                ))}
              </section>
              <section className="card stack">
                <h2>Доступ инструктора</h2>
                <p className="small muted">
                  Можно временно открыть конкретное занятие для заполнения или исправления отчёта.
                </p>
                {!data.bookings.some((b) => !['planned', 'arrival_window'].includes(b.status)) && (
                  <p className="small muted">Занятий для повторного доступа пока нет.</p>
                )}
                {data.bookings
                  .filter((b) => !['planned', 'arrival_window'].includes(b.status))
                  .slice(0, 8)
                  .map((b) => (
                    <div key={b.id}>
                      <p className="small">
                        {dateLabel(b.date)} · {b.start_at}
                      </p>
                      <p className="small muted" style={{ margin: '4px 0' }}>
                        {b.instructor?.full_name}
                      </p>
                      <button className="text-btn" onClick={() => setGrant(b)}>
                        <KeyRound size={14} />
                        Открыть на время
                      </button>
                    </div>
                  ))}
              </section>
              {data.profile.client.notes_internal && (
                <section className="card stack">
                  <h2>Заметка администратора</h2>
                  <p className="small muted" style={{ whiteSpace: 'pre-wrap' }}>
                    {data.profile.client.notes_internal}
                  </p>
                </section>
              )}
              <Link className="btn ghost" to="/audit">
                <ShieldCheck size={16} />
                Журнал изменений
              </Link>
            </aside>
          </div>
        )
      )}
      {viewing && data && (
        <Modal title="Оценки и результат занятия" onClose={() => setViewing(null)}>
          <LessonDetails
            item={data.profile.history.find((h) => h.booking_id === viewing.booking_id) || viewing}
            timezone={data.profile.timezone}
          />
          {viewing.report_id && (
            <button
              className="btn secondary full"
              onClick={() => {
                setEditing(viewing)
                setViewing(null)
              }}
            >
              <PenLine size={16} />
              Исправить отчёт с указанием причины
            </button>
          )}
        </Modal>
      )}
      {editing && (
        <Modal title="Исправить отчёт" onClose={() => setEditing(null)}>
          <AdminReport
            reportId={editing.report_id!}
            onSaved={() => {
              setEditing(null)
              setNotice(
                'Отчёт исправлен. Оценка вождения пересчитана, изменение сохранено в аудите.',
              )
              reload()
            }}
          />
        </Modal>
      )}
      {grant && (
        <Modal title="Повторный доступ" onClose={() => setGrant(null)}>
          <GrantForm
            booking={grant}
            onSaved={() => {
              setGrant(null)
              setNotice('Временный доступ открыт.')
              reload()
            }}
          />
        </Modal>
      )}
      {draft && !conclusion && (
        <Modal title="Черновик заключения" onClose={() => setDraft(null)}>
          <span className="badge amber">Сформировано ИИ — требуется утверждение</span>
          <p className="small" style={{ whiteSpace: 'pre-wrap', lineHeight: 1.9 }}>
            {draft.generated_text}
          </p>
          <p className="small muted">
            {draft.provider} · {draft.model}
          </p>
          <button className="btn" onClick={() => setConclusion(true)}>
            Проверить и оформить заключение
          </button>
        </Modal>
      )}
      {conclusion && (
        <Modal title="Новое заключение школы" onClose={() => setConclusion(false)}>
          <ConclusionForm
            clientId={Number(id)}
            profile={data?.profile}
            draft={draft || undefined}
            onSaved={() => {
              setConclusion(false)
              setDraft(null)
              setNotice('Новая версия заключения сохранена.')
              reload()
            }}
          />
        </Modal>
      )}
      {booklet && data && (
        <Modal title="История для бумажной книжки" onClose={() => setBooklet(false)}>
          <p className="small muted">
            {data.profile.client.full_name}. Даты, часы, упражнения и оценки для ручного переноса в
            практические разделы.
          </p>
          <div className="booklet">
            <h2>{data.profile.client.full_name}</h2>
            <p className="small">
              История практических занятий · {data.profile.stats.total_hours} часов
            </p>
            {data.profile.history
              .filter((h) => h.report_id)
              .map((h) => (
                <article className="history-row" key={h.booking_id}>
                  <h3>
                    {dateLabel(h.date)} · {h.context}
                  </h3>
                  <p className="small muted">
                    {h.start_at}–{h.end_at} · {h.duration_minutes} мин · {h.instructor}
                  </p>
                  <p className="small" style={{ marginTop: 10 }}>
                    {h.exercises?.map((e) => e.name).join('; ') || 'Упражнения не указаны'}
                  </p>
                  <p className="small">
                    Оценка: {h.overall_grade == null ? 'не указана' : h.overall_grade + '/5'}
                  </p>
                  {h.autonomy_level && (
                    <p className="small">Самостоятельность: {h.autonomy_level}</p>
                  )}
                  {h.quick_verdict && <p className="small">Вердикт: {h.quick_verdict}</p>}
                  {h.comment_internal && (
                    <p className="small" style={{ whiteSpace: 'pre-wrap' }}>
                      Рекомендации инструктора: {h.comment_internal}
                    </p>
                  )}
                </article>
              ))}
          </div>
          <button className="btn" onClick={() => window.print()}>
            <Printer size={16} />
            Распечатать
          </button>
        </Modal>
      )}
    </div>
  )
}
function LessonDetails({ item, timezone }: { item: HistoryItem; timezone?: string }) {
  const timestamp = (value: string) =>
    dateLabel(value, {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      timeZone: timezone || 'Asia/Almaty',
    })
  return (
    <div className="stack lesson-details">
      <div className="row between wrap">
        <h3>{dateLabel(item.date, { day: 'numeric', month: 'long', year: 'numeric' })}</h3>
        <Status value={item.status} />
      </div>
      <dl className="lesson-facts">
        <div>
          <dt>Время школы</dt>
          <dd>
            {item.start_at}–{item.end_at}
          </dd>
        </div>
        <div>
          <dt>Условия</dt>
          <dd>{item.context}</dd>
        </div>
        <div>
          <dt>Инструктор</dt>
          <dd>{item.instructor}</dd>
        </div>
        {item.duration_minutes != null && (
          <div>
            <dt>Длительность</dt>
            <dd>{item.duration_minutes} мин</dd>
          </div>
        )}
      </dl>
      {!item.report_id ? (
        <Empty
          title="Отчёт инструктора отсутствует"
          text={
            item.status === 'no_show'
              ? 'Зафиксирована неявка. Оценки навыков за это занятие не выставлялись.'
              : 'Упражнения, оценки и рекомендации появятся после сохранения отчёта инструктором.'
          }
        />
      ) : (
        <>
          <dl className="lesson-facts">
            <div>
              <dt>Общая оценка</dt>
              <dd>{item.overall_grade == null ? 'Не указана' : item.overall_grade + ' / 5'}</dd>
            </div>
            <div>
              <dt>Самостоятельность</dt>
              <dd>{item.autonomy_level || 'Не указана'}</dd>
            </div>
            {item.formula_version != null && (
              <div>
                <dt>Версия методики</dt>
                <dd>{item.formula_version}</dd>
              </div>
            )}
          </dl>
          <section className="stack">
            <h3>Что отрабатывали</h3>
            {item.exercises?.length ? (
              <ul className="lesson-exercises">
                {item.exercises.map((exercise, index) => (
                  <li key={index}>
                    {exercise.name}
                    {exercise.section && <span className="muted"> · {exercise.section}</span>}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="small muted">Упражнения в отчёте не указаны.</p>
            )}
          </section>
          <section className="stack">
            <h3>Оценки навыков инструктора</h3>
            {item.skills?.length ? (
              <div className="lesson-skills">
                {item.skills.map((skill) => (
                  <div className="row between" key={skill.skill_id}>
                    <div className="grow">
                      <p className="small">{skill.name || 'Критерий №' + skill.skill_id}</p>
                      <p className="small muted">Версия критерия {skill.version}</p>
                    </div>
                    <strong className="badge blue">{skill.value} / 4</strong>
                  </div>
                ))}
              </div>
            ) : (
              <p className="small muted">Оценки отдельных навыков отсутствуют.</p>
            )}
          </section>
          <section className="stack">
            <h3>Вмешательства и безопасность</h3>
            {item.interventions?.length ? (
              item.interventions.map((intervention, index) => (
                <div
                  className={'lesson-event' + (intervention.is_critical ? ' critical' : '')}
                  key={index}
                >
                  <p className="small">
                    {intervention.type === 'нет' ? 'Без вмешательства' : intervention.type}
                  </p>
                  {intervention.is_critical && (
                    <span className="badge red">Критическое событие</span>
                  )}
                  {intervention.reason && (
                    <p className="small muted">Причина: {intervention.reason}</p>
                  )}
                  {intervention.description && (
                    <p className="small" style={{ whiteSpace: 'pre-wrap' }}>
                      {intervention.description}
                    </p>
                  )}
                </div>
              ))
            ) : (
              <p className="small muted">В отчёте нет сведений о вмешательствах.</p>
            )}
          </section>
          <section className="stack">
            <h3>Вердикт и дальнейшая работа</h3>
            <p className="small">{item.quick_verdict || 'Вердикт не указан.'}</p>
            <p className="small muted" style={{ whiteSpace: 'pre-wrap' }}>
              {item.comment_internal || 'Комментарий инструктора не указан.'}
            </p>
          </section>
          <p className="small muted">
            Отчёт №{item.report_id}
            {item.created_at && <> · Сохранён {timestamp(item.created_at)}</>}
            {item.last_edited_at && <> · Исправлен {timestamp(item.last_edited_at)}</>}
          </p>
        </>
      )}
    </div>
  )
}
function AdminReport({ reportId, onSaved }: { reportId: number; onSaved: () => void }) {
  const reason = useRef('')
  const [context, setContext] = useState('')
  const { data, error, loading } = useResource(async () => {
    const report = await adminApi.get<ReportInput>('/reports/' + reportId)
    const actual = context || report.context
    const [skills, exercises, verdicts, reasons] = await Promise.all(
      ['skills', 'exercises', 'verdicts', 'reasons'].map((k) =>
        adminApi.get<CatalogItem[]>('/catalogs/' + k, k === 'verdicts' ? {} : { context: actual }),
      ),
    )
    return {
      report:
        actual === report.context
          ? report
          : { ...report, context: actual, skills: [], exercises: [] },
      skills,
      exercises,
      verdicts,
      reasons,
    }
  }, reportId + context)
  if (loading) return <Loading />
  if (error) return <ErrorBox message={error} />
  if (!data) return null
  return (
    <div className="stack">
      <label className="field">
        Контекст занятия
        <select value={context || data.report.context} onChange={(e) => setContext(e.target.value)}>
          <option>Учебная площадка</option>
          <option>Город</option>
        </select>
      </label>
      <ReportEditor
        key={context}
        context={data.report.context}
        skills={data.skills}
        exercises={data.exercises}
        verdicts={data.verdicts}
        reasons={data.reasons}
        initial={data.report}
        requireReason
        onReason={(r) => {
          reason.current = r
        }}
        submitLabel="Сохранить исправление"
        onSubmit={async (report) => {
          await adminApi.patch('/reports/' + reportId, { report, reason: reason.current })
          onSaved()
        }}
      />
    </div>
  )
}
function ConclusionForm({
  clientId,
  profile,
  draft,
  onSaved,
}: {
  clientId: number
  profile?: Profile
  draft?: Draft
  onSaved: () => void
}) {
  const [text, setText] = useState(draft?.generated_text || ''),
    [status, setStatus] = useState(''),
    [approver, setApprover] = useState('admin'),
    [busy, setBusy] = useState(false),
    [error, setError] = useState('')
  const {
    data,
    error: loadError,
    loading,
    reload,
  } = useResource(async () => {
    const [instructors, settings] = await Promise.all([
      adminApi.get<Person[]>('/instructors'),
      adminApi.get<{ conclusion_statuses: string[] }>('/settings'),
    ])
    return { instructors, statuses: settings.conclusion_statuses }
  })
  return (
    <form
      className="stack"
      onSubmit={async (e) => {
        e.preventDefault()
        setBusy(true)
        setError('')
        try {
          await adminApi.post('/clients/' + clientId + '/conclusions', {
            status,
            text,
            ai_draft_id: draft?.id,
            approved_by_type: approver === 'admin' ? 'admin' : 'instructor',
            approved_by_id: approver === 'admin' ? 0 : Number(approver),
          })
          onSaved()
        } catch (e) {
          setError(errorMessage(e))
        } finally {
          setBusy(false)
        }
      }}
    >
      {profile && (
        <div className="alert info">
          <div>
            <p>
              Основание: {profile.stats.total_lessons} завершённых занятий; площадка —{' '}
              {profile.stats.ground_lessons}, город — {profile.stats.city_lessons}.
            </p>
            <p>
              Общая оценка:{' '}
              {profile.scores.overall.score == null
                ? profile.scores.overall.status
                : profile.scores.overall.score + ' / 100 · ' + profile.scores.overall.status}
              .
            </p>
            {profile.flags.some((flag) => flag.active) && (
              <p>Есть активные замечания по обучению. Учтите их при формулировке заключения.</p>
            )}
          </div>
        </div>
      )}
      {draft && (
        <div className="alert info">
          Проверьте факты и рекомендации в ИИ-черновике перед утверждением.
        </div>
      )}
      <label className="field">
        Вывод школы
        <select
          required
          disabled={!data}
          value={status}
          onChange={(e) => setStatus(e.target.value)}
        >
          <option value="">Выберите вывод по результатам обучения</option>
          {data?.statuses.map((s) => (
            <option key={s}>{s}</option>
          ))}
        </select>
      </label>
      <label className="field">
        Текст заключения *
        <textarea
          required
          minLength={10}
          maxLength={10000}
          rows={10}
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
      </label>
      <label className="field">
        Кто фактически утвердил
        <select value={approver} onChange={(e) => setApprover(e.target.value)}>
          <option value="admin">Администратор</option>
          {data?.instructors.map((i) => (
            <option key={i.id} value={i.id}>
              {i.full_name} · инструктор
            </option>
          ))}
        </select>
      </label>
      <p className="small muted">
        Будет сохранена новая версия. Предыдущие заключения останутся в истории.
      </p>
      <ErrorBox message={error} />
      <ErrorBox message={loadError} retry={reload} />
      <button className="btn full" disabled={busy || loading || !data || !status}>
        <FileCheck size={17} />
        {busy ? 'Сохраняем…' : 'Утвердить заключение'}
      </button>
    </form>
  )
}
