import { useEffect, useState } from 'react'
import { AlertTriangle, Check, ChevronDown, ChevronUp, Save } from 'lucide-react'
import { CatalogItem, ReportInput, Booking, dateLabel, contextLabel } from '../../../shared/types'
import { Avatar, ErrorBox } from './UI'
import { errorMessage } from '../../../shared/errors'

interface Props {
  context: string
  skills: CatalogItem[]
  exercises: CatalogItem[]
  verdicts: CatalogItem[]
  reasons: CatalogItem[]
  initial?: ReportInput
  draftKey?: string
  booking?: Booking
  onSubmit: (data: ReportInput) => Promise<void>
  submitLabel?: string
  requireReason?: boolean
  onReason?: (reason: string) => void
}

export default function ReportEditor({
  context,
  skills,
  exercises,
  verdicts,
  reasons,
  initial,
  draftKey,
  booking,
  onSubmit,
  submitLabel = 'Завершить отчёт',
  requireReason,
  onReason,
}: Props) {
  const blank: ReportInput = {
    context,
    skills: [],
    exercises: [],
    overall_grade_1_5: 0,
    autonomy_level: '',
    intervention: { type: '', is_critical: false },
    comment_internal: '',
    quick_verdict: '',
  }

  const [form, setForm] = useState<ReportInput>(() => {
    if (initial) return initial
    try {
      const saved = draftKey && sessionStorage.getItem(draftKey)
      if (saved) {
        const parsed = JSON.parse(saved)
        if (
          parsed.context === context &&
          Array.isArray(parsed.skills) &&
          Array.isArray(parsed.exercises)
        ) {
          return parsed
        }
      }
    } catch {}
    return blank
  })

  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [savedDraft, setSavedDraft] = useState(false)
  const [reason, setReason] = useState('')
  const [showAllExercises, setShowAllExercises] = useState(false)
  const [online, setOnline] = useState(navigator.onLine)
  const [expandedSkill, setExpandedSkill] = useState<number | null>(skills[0]?.id || null)

  useEffect(() => {
    const update = () => setOnline(navigator.onLine)
    window.addEventListener('online', update)
    window.addEventListener('offline', update)
    return () => {
      window.removeEventListener('online', update)
      window.removeEventListener('offline', update)
    }
  }, [])

  useEffect(() => {
    if (draftKey) {
      try {
        sessionStorage.setItem(draftKey, JSON.stringify(form))
      } catch {}
    }
  }, [form, draftKey])

  const update = (patch: Partial<ReportInput>) => {
    setForm((f) => ({ ...f, ...patch }))
    setSavedDraft(false)
  }

  const handleScoreSkill = (skillId: number, value: number) => {
    update({
      skills: [...form.skills.filter((s) => s.skill_id !== skillId), { skill_id: skillId, value }],
    })
  }

  const getSkillVisualGrade = (skillId: number): number | null => {
    const item = form.skills.find((s) => s.skill_id === skillId)
    if (!item) return null
    return item.value
  }

  const handleSaveDraft = () => {
    if (draftKey) {
      try {
        sessionStorage.setItem(draftKey, JSON.stringify(form))
        setSavedDraft(true)
        window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('success')
        setTimeout(() => setSavedDraft(false), 3000)
      } catch {
        setError('Не удалось сохранить черновик.')
      }
    }
  }

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (!form.exercises.length) {
      setError('Выберите хотя бы одно упражнение, которое отрабатывали.')
      return
    }

    if (!form.skills.length) {
      setError('Оцените хотя бы один навык вождения.')
      return
    }

    if (!form.overall_grade_1_5) {
      setError('Укажите общую оценку занятия.')
      return
    }

    if (!form.autonomy_level) {
      setError('Укажите уровень самостоятельности ученика.')
      return
    }

    if (!form.intervention.type) {
      setError('Укажите, требовалось ли вмешательство инструктора.')
      return
    }

    if (form.intervention.is_critical && !form.intervention.description?.trim()) {
      setError('Опишите критическое событие.')
      return
    }

    if (
      form.intervention.type === 'физическое вмешательство' &&
      !form.intervention.reason?.trim()
    ) {
      setError('Укажите причину физического вмешательства.')
      return
    }

    if (requireReason && !reason.trim()) {
      setError('Укажите причину исправления для журнала аудита.')
      return
    }

    if (!navigator.onLine) {
      setError('Нет связи. Дождитесь подключения перед отправкой отчёта.')
      return
    }

    setBusy(true)
    try {
      onReason?.(reason)
      await onSubmit(form)
      if (draftKey) sessionStorage.removeItem(draftKey)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="report-editor-screen" onSubmit={submit}>
      {/* 1. Student Card Header (Screen 3 in mockup) */}
      {booking && (
        <div className="report-student-card">
          <Avatar name={booking.client.full_name} />
          <div className="report-student-meta">
            <h3 className="report-student-name">{booking.client.full_name}</h3>
            <p className="report-student-timing">
              {dateLabel(booking.date)}, {booking.start_at} – {booking.end_at}
            </p>
            <span className="report-context-pill">{contextLabel(booking.context)}</span>
          </div>
        </div>
      )}

      {/* 2. Skills Assessment (Screen 3: 'Оцените занятие') */}
      <section className="report-section-box">
        <h2 className="report-section-title">Оценки навыков</h2>
        <p className="aux-note">
          Шкала навыков: от 0 до 4. Оцените только навыки, которые наблюдали на занятии. Неоценённые
          навыки не считаются нулём.
        </p>
        {!skills.length && (
          <ErrorBox message="Справочник навыков пуст. Обратитесь к администратору школы." />
        )}

        <div className="skills-evaluation-stack">
          {skills.map((skill) => {
            const currentVisual = getSkillVisualGrade(skill.id)
            const isOpened = expandedSkill === skill.id

            return (
              <div key={skill.id} className="skill-rating-item">
                <div
                  className="skill-rating-header"
                  onClick={() => setExpandedSkill(isOpened ? null : skill.id)}
                >
                  <span className="skill-name-text">{skill.name}</span>
                  <button
                    type="button"
                    className="skill-chevron-toggle"
                    aria-label="Свернуть/Развернуть"
                  >
                    {isOpened ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                  </button>
                </div>

                <div className="skill-pills-row">
                  {[0, 1, 2, 3, 4].map((n) => (
                    <button
                      key={n}
                      type="button"
                      className={'skill-pill-num ' + (currentVisual === n ? 'is-active' : '')}
                      aria-label={`${skill.name}: ${n}`}
                      aria-pressed={currentVisual === n}
                      onClick={() => handleScoreSkill(skill.id, n)}
                    >
                      {n}
                    </button>
                  ))}
                </div>
                {isOpened && currentVisual !== null && (
                  <button
                    type="button"
                    className="text-toggle-btn"
                    onClick={() =>
                      update({ skills: form.skills.filter((item) => item.skill_id !== skill.id) })
                    }
                  >
                    Убрать оценку: навык не наблюдался
                  </button>
                )}
              </div>
            )
          })}
        </div>
      </section>

      <section className="report-section-box">
        <h2 className="report-section-title">Общая оценка занятия</h2>
        <div className="skill-pills-row" role="group" aria-label="Общая оценка занятия от 1 до 5">
          {[1, 2, 3, 4, 5].map((grade) => (
            <button
              key={grade}
              type="button"
              className={'skill-pill-num ' + (form.overall_grade_1_5 === grade ? 'is-active' : '')}
              aria-pressed={form.overall_grade_1_5 === grade}
              onClick={() => update({ overall_grade_1_5: grade })}
            >
              {grade}
            </button>
          ))}
        </div>
      </section>

      {/* 3. Autonomy Level */}
      <section className="report-section-box">
        <h2 className="report-section-title">Самостоятельность</h2>
        <div className="skill-pills-row autonomy-row">
          {[
            ['A0', 'Помощь'],
            ['A1', 'Подсказки'],
            ['A2', 'Редко'],
            ['A3', 'Сам'],
          ].map(([code, label]) => (
            <button
              key={code}
              type="button"
              className={
                'skill-pill-num autonomy-pill ' +
                (form.autonomy_level.startsWith(code) ? 'is-active' : '')
              }
              onClick={() => update({ autonomy_level: code })}
            >
              <span className="autonomy-code">{code}</span>
              <span className="autonomy-label">{label}</span>
            </button>
          ))}
        </div>
      </section>

      {/* 4. Exercises list ('Что отрабатывали') */}
      {exercises.length > 0 && (
        <section className="report-section-box">
          <div className="report-section-row-between">
            <h2 className="report-section-title">Что отрабатывали</h2>
            <span className="badge-pill-counter">{form.exercises.length} выбрано</span>
          </div>

          <div className="exercises-chips-grid">
            {(showAllExercises ? exercises : exercises.slice(0, 6)).map((ex) => {
              const isSelected = form.exercises.some((e) => e.exercise_id === ex.id)
              return (
                <button
                  type="button"
                  key={ex.id}
                  className={'exercise-chip ' + (isSelected ? 'is-selected' : '')}
                  onClick={() =>
                    update({
                      exercises: isSelected
                        ? form.exercises.filter((e) => e.exercise_id !== ex.id)
                        : [...form.exercises, { exercise_id: ex.id }],
                    })
                  }
                >
                  {isSelected && <Check size={13} className="exercise-chip-check" />}
                  <span>{ex.short_name || ex.name}</span>
                </button>
              )
            })}
          </div>

          {exercises.length > 6 && (
            <button
              type="button"
              className="text-toggle-btn"
              onClick={() => setShowAllExercises(!showAllExercises)}
            >
              {showAllExercises ? 'Свернуть' : 'Все упражнения'}
              <ChevronDown size={14} />
            </button>
          )}
        </section>
      )}
      {!exercises.length && (
        <ErrorBox message="Справочник упражнений пуст. Обратитесь к администратору школы." />
      )}

      {/* 5. Critical Events Toggle (Screen 3 switch) */}
      <section className="report-section-box">
        <label className="report-field-label">
          Вмешательство инструктора
          <select
            className="ios-select-input"
            value={form.intervention.type}
            onChange={(e) => update({ intervention: { type: e.target.value, is_critical: false } })}
          >
            <option value="">Выберите тип вмешательства</option>
            <option value="нет">Не требовалось</option>
            <option value="словесная подсказка">Словесная подсказка</option>
            <option value="физическое вмешательство">Физическое вмешательство</option>
          </select>
        </label>
        <div className="critical-toggle-row">
          <div className="critical-icon-col">
            <AlertTriangle size={22} className="critical-warning-icon" />
          </div>
          <div className="critical-text-col">
            <div className="critical-title">Критические события</div>
            <div className="critical-subtitle">ДТП, опасные ситуации, грубые нарушения</div>
          </div>
          <label className="ios-toggle-switch">
            <input
              type="checkbox"
              disabled={!form.intervention.type || form.intervention.type === 'нет'}
              checked={form.intervention.is_critical}
              onChange={(e) =>
                update({
                  intervention: {
                    ...form.intervention,
                    is_critical: e.target.checked,
                  },
                })
              }
            />
            <span className="ios-toggle-slider" />
          </label>
        </div>

        {form.intervention.type && form.intervention.type !== 'нет' && (
          <div className="critical-details-expand">
            <label className="report-field-label">
              Причина вмешательства
              <select
                className="ios-select-input"
                value={form.intervention.reason || ''}
                onChange={(e) =>
                  update({ intervention: { ...form.intervention, reason: e.target.value } })
                }
              >
                <option value="">Выберите причину</option>
                {reasons.map((r) => (
                  <option key={r.id} value={r.name}>
                    {r.name}
                  </option>
                ))}
              </select>
            </label>

            {!reasons.length && (
              <label className="report-field-label">
                Причина вмешательства
                <input
                  className="ios-select-input"
                  value={form.intervention.reason || ''}
                  maxLength={500}
                  onChange={(e) =>
                    update({ intervention: { ...form.intervention, reason: e.target.value } })
                  }
                  placeholder="Укажите причину"
                />
              </label>
            )}

            <label className="report-field-label">
              Что произошло
              <textarea
                className="ios-textarea-input"
                maxLength={1000}
                value={form.intervention.description || ''}
                onChange={(e) =>
                  update({ intervention: { ...form.intervention, description: e.target.value } })
                }
                placeholder="Опишите ситуацию и вмешательство инструктора"
              />
            </label>
          </div>
        )}
      </section>

      {/* 6. Comment Section (Screen 3: 'Комментарий') */}
      <section className="report-section-box">
        <label className="report-section-title" htmlFor="instructor-comment">
          Комментарий
        </label>
        <textarea
          id="instructor-comment"
          className="ios-textarea-input"
          maxLength={500}
          rows={3}
          value={form.comment_internal || ''}
          onChange={(e) => update({ comment_internal: e.target.value })}
          placeholder="Ваш комментарий о занятии..."
        />
        <div className="comment-char-count">{form.comment_internal?.length || 0}/500</div>
      </section>

      {/* Quick Verdict (optional) */}
      {verdicts.length > 0 && (
        <section className="report-section-box">
          <label className="report-section-title">
            Вердикт школы
            <select
              className="ios-select-input"
              value={form.quick_verdict || ''}
              onChange={(e) => update({ quick_verdict: e.target.value })}
            >
              <option value="">Без вердикта</option>
              {verdicts.map((v) => (
                <option key={v.id} value={v.name}>
                  {v.name}
                </option>
              ))}
            </select>
          </label>
        </section>
      )}

      {requireReason && (
        <section className="report-section-box">
          <label className="report-section-title">
            Причина исправления *
            <textarea
              required
              className="ios-textarea-input"
              value={reason}
              onChange={(e) => {
                setReason(e.target.value)
                onReason?.(e.target.value)
              }}
              placeholder="Укажите причину изменения отчёта"
              maxLength={1000}
            />
          </label>
        </section>
      )}

      <ErrorBox message={error} />

      {/* 7. Bottom Dual Action Buttons (Screen 3 in mockup) */}
      <div className="report-dual-actions-bar">
        {draftKey && (
          <button
            type="button"
            className="btn-draft-secondary"
            onClick={handleSaveDraft}
            disabled={busy}
          >
            <Save size={16} />
            <span>{savedDraft ? 'Сохранено' : 'Сохранить черновик'}</span>
          </button>
        )}

        <button type="submit" className="btn-submit-primary" disabled={busy || !online}>
          {busy ? (
            'Сохраняем…'
          ) : (
            <>
              <Check size={18} />
              <span>{submitLabel}</span>
            </>
          )}
        </button>
      </div>
    </form>
  )
}
