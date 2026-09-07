import { useEffect, useState } from 'react'
import { Link, useParams, useSearchParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, ArrowRight, Check, RotateCcw } from 'lucide-react'
import { api } from '../services/api'
import { ErrorBox, Loading, ScoreRing, useResource } from '../components/UI'
import ReportEditor from '../components/ReportEditor'
import { ReportResult } from '../../../shared/types'
import { useInstructor } from '../App'

export default function ReportPage() {
  const { bookingId } = useParams()
  const [search] = useSearchParams()
  const navigate = useNavigate()
  const edit = Number(search.get('edit')) || null
  const instructor = useInstructor()
  const [result, setResult] = useState<ReportResult | null>(null)

  const { data, error, loading, reload } = useResource(
    async () => {
      const booking = await api.getBooking(Number(bookingId))
      const [skills, exercises, verdicts, reasons, report] = await Promise.all([
        api.getSkills(booking.context),
        api.getExercises(booking.context),
        api.getVerdicts(),
        api.getInterventionReasons(booking.context),
        edit ? api.getReport(edit) : Promise.resolve(undefined),
      ])
      return {
        booking,
        skills: skills.skills,
        exercises: exercises.exercises,
        verdicts: verdicts.verdicts,
        reasons: reasons.reasons,
        report,
      }
    },
    bookingId + ':' + edit,
  )

  useEffect(() => {
    const tg = window.Telegram?.WebApp
    if (!result && tg?.isVersionAtLeast?.('6.2')) tg.enableClosingConfirmation?.()
    const before = (e: BeforeUnloadEvent) => {
      if (!result) {
        e.preventDefault()
        e.returnValue = ''
      }
    }
    window.addEventListener('beforeunload', before)
    return () => {
      tg?.disableClosingConfirmation?.()
      window.removeEventListener('beforeunload', before)
    }
  }, [result])

  if (loading && !data) return <Loading />

  if (error) {
    return (
      <div className="report-page-wrap">
        <div className="ios-page-head">
          <Link to="/" className="ios-back-link" aria-label="Назад">
            <ArrowLeft size={20} />
          </Link>
          <h1 className="ios-page-title">Отчёт</h1>
        </div>
        <div className="directory-content-stack" style={{ marginTop: 20 }}>
          <ErrorBox message={error} retry={reload} />
          <Link
            to="/"
            className="btn-submit-primary"
            style={{ textDecoration: 'none', justifyContent: 'center' }}
          >
            К расписанию
          </Link>
        </div>
      </div>
    )
  }

  if (!data) return null

  // ---------------------------------------------------------------------------
  // SCREEN 4: Результат отчёта (Screen 4 in mockup)
  // ---------------------------------------------------------------------------
  if (result) {
    const overallScore = result.scores.overall
    const groundScore = result.scores.ground
    const cityScore = result.scores.city

    return (
      <div className="report-success-screen">
        {/* Success Header */}
        <div className="success-icon-badge">
          <Check size={40} />
        </div>
        <h1 className="success-screen-title">{edit ? 'Отчёт обновлён!' : 'Отчёт сохранён!'}</h1>
        <p className="success-screen-sub">Оценки сохранены в истории обучения</p>

        {/* Score Card: Screen 4 in mockup */}
        <section className="score-summary-card">
          <h3 className="score-summary-title">Оценка вождения</h3>

          <div className="score-ring-row">
            <ScoreRing score={overallScore} />
            <div className="score-trend-info">
              <div className="score-trend-label">
                {overallScore === null
                  ? 'Общая оценка появится, когда будет достаточно данных по площадке и городу.'
                  : 'Рассчитано по сохранённым оценкам навыков и самостоятельности.'}
              </div>
            </div>
          </div>

          {/* 3 Metric Pills with deltas */}
          <div className="score-pills-row">
            <div className="score-pill-card pill-ground">
              <div className="score-pill-value">{groundScore ?? '—'}</div>
              <div className="score-pill-name">Площадка</div>
              {groundScore === null && <div className="score-pill-delta">Нет оценки</div>}
            </div>

            <div className="score-pill-card pill-city">
              <div className="score-pill-value">{cityScore ?? '—'}</div>
              <div className="score-pill-name">Город</div>
              {cityScore === null && <div className="score-pill-delta">Нет оценки</div>}
            </div>

            <div className="score-pill-card pill-overall">
              <div className="score-pill-value">{overallScore ?? '—'}</div>
              <div className="score-pill-name">Общая готовность</div>
              {overallScore === null && <div className="score-pill-delta">Недостаточно данных</div>}
            </div>
          </div>
        </section>

        {/* Action Buttons */}
        <div className="success-actions-stack">
          <Link className="btn-draft-secondary aux-link-button" to={'/lessons/' + data.booking.id}>
            Просмотреть сохранённый отчёт
          </Link>
          <Link
            className="btn-submit-primary"
            style={{ textDecoration: 'none', justifyContent: 'center' }}
            to={'/client/' + data.booking.client.id}
          >
            <span>Перейти к профилю ученика</span>
            <ArrowRight size={18} />
          </Link>

          <Link
            className="btn-draft-secondary"
            style={{ textDecoration: 'none', justifyContent: 'center' }}
            to="/"
          >
            <span>Вернуться к расписанию</span>
          </Link>
        </div>
      </div>
    )
  }

  const unavailable = edit ? !data.report?.can_edit : !data.booking.actions?.includes('report')

  // ---------------------------------------------------------------------------
  // SCREEN 3: Создание отчёта (Screen 3 in mockup)
  // ---------------------------------------------------------------------------
  return (
    <div className="report-page-wrap">
      <div className="ios-page-head">
        <button
          type="button"
          onClick={() => navigate(-1)}
          className="ios-back-link"
          aria-label="Назад"
        >
          <ArrowLeft size={20} />
        </button>
        <h1 className="ios-page-title">{edit ? 'Исправление отчёта' : 'Оценка занятия'}</h1>
      </div>

      {unavailable ? (
        <div className="directory-content-stack" style={{ marginTop: 20 }}>
          <ErrorBox message="Оценка сейчас недоступна. Завершите занятие в расписании или обратитесь к администратору для повторного доступа." />
          {data.booking.report_id && (
            <Link className="btn-submit-primary aux-link-button" to={'/lessons/' + data.booking.id}>
              Просмотреть отчёт
            </Link>
          )}
          <Link
            to="/"
            className="btn-draft-secondary"
            style={{ textDecoration: 'none', justifyContent: 'center' }}
          >
            <RotateCcw size={16} />
            <span>Вернуться к расписанию</span>
          </Link>
        </div>
      ) : (
        <ReportEditor
          context={data.booking.context}
          skills={data.skills}
          exercises={data.exercises}
          verdicts={data.verdicts}
          reasons={data.reasons}
          initial={data.report}
          booking={data.booking}
          draftKey={edit ? undefined : 'report-draft:' + instructor.id + ':' + bookingId}
          onSubmit={async (form) => {
            const saved = edit
              ? await api.updateReport(edit, form)
              : await api.createReport(Number(bookingId), form)
            setResult(saved)
            window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('success')
            window.scrollTo(0, 0)
          }}
        />
      )}
    </div>
  )
}
