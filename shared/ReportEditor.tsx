import { useEffect, useState } from 'react'
import { AlertTriangle, Check, ChevronDown, ClipboardCheck, Save } from 'lucide-react'
import { CatalogItem, ReportInput } from './types'
import { ErrorBox } from './UI'
import { errorMessage } from './errors'
interface Props {
  context: string
  skills: CatalogItem[]
  exercises: CatalogItem[]
  verdicts: CatalogItem[]
  reasons: CatalogItem[]
  initial?: ReportInput
  draftKey?: string
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
  onSubmit,
  submitLabel = 'Сохранить отчёт',
  requireReason,
  onReason,
}: Props) {
  const blank: ReportInput = {
    context,
    skills: [],
    exercises: [],
    overall_grade_1_5: 0,
    autonomy_level: '',
    intervention: { type: 'нет', is_critical: false },
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
        )
          return parsed
      }
    } catch {}
    return blank
  })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(false)
  const [reason, setReason] = useState('')
  const [showExercises, setShowExercises] = useState(false)
  const [online, setOnline] = useState(navigator.onLine)
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
    setSaved(false)
  }
  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    if (!form.exercises.length) {
      setError('Выберите хотя бы одно упражнение, которое отрабатывали.')
      return
    }
    if (!form.skills.length) {
      setError('Оцените хотя бы один навык. Остальные можно оставить без оценки.')
      return
    }
    if (!form.overall_grade_1_5 || !form.autonomy_level) {
      setError('Укажите общую оценку и самостоятельность ученика.')
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
      setError('Нет связи. Ваши оценки сохранены в текущей сессии.')
      return
    }
    setBusy(true)
    try {
      onReason?.(reason)
      await onSubmit(form)
      if (draftKey) sessionStorage.removeItem(draftKey)
    } catch (e) {
      setError(errorMessage(e))
    } finally {
      setBusy(false)
    }
  }
  const scoreSkill = (id: number, value: number | null) =>
    update({
      skills: [
        ...form.skills.filter((s) => s.skill_id !== id),
        ...(value === null ? [] : [{ skill_id: id, value }]),
      ],
    })
  return (
    <form className="report-form" onSubmit={submit}>
      <fieldset
        disabled={busy}
        style={{ border: 0, padding: 0, margin: 0, minWidth: 0, display: 'contents' }}
      >
        <section className="card stack">
          <div className="row between">
            <h2>Что отрабатывали</h2>
            <span className="badge blue">{form.exercises.length} выбрано</span>
          </div>
          <div className="chips">
            {(showExercises ? exercises : exercises.slice(0, 6)).map((ex) => (
              <button
                type="button"
                className={
                  'chip ' + (form.exercises.some((e) => e.exercise_id === ex.id) ? 'selected' : '')
                }
                aria-pressed={form.exercises.some((e) => e.exercise_id === ex.id)}
                key={ex.id}
                onClick={() =>
                  update({
                    exercises: form.exercises.some((e) => e.exercise_id === ex.id)
                      ? form.exercises.filter((e) => e.exercise_id !== ex.id)
                      : [...form.exercises, { exercise_id: ex.id }],
                  })
                }
              >
                {form.exercises.some((e) => e.exercise_id === ex.id) && (
                  <Check size={12} style={{ marginRight: 5 }} />
                )}
                {ex.short_name}
              </button>
            ))}
          </div>
          {exercises.length > 6 && (
            <button
              type="button"
              className="text-btn"
              onClick={() => setShowExercises(!showExercises)}
            >
              {showExercises ? 'Свернуть' : 'Все упражнения'}
              <ChevronDown size={14} />
            </button>
          )}
          {!exercises.length && (
            <ErrorBox message="Нет упражнений для этого занятия. Администратор должен заполнить справочник." />
          )}
        </section>
        <section className="card">
          <div className="row between">
            <h2>Оцените навыки</h2>
            <ClipboardCheck size={19} color="var(--blue)" />
          </div>
          <p className="small muted" style={{ marginTop: 8 }}>
            0 — не выполняет · 4 — уверенно и безопасно.
            <br />
            «—» — не оценивалось, в расчёт не входит.
          </p>
          {skills.map((skill) => (
            <div className="rating-row" key={skill.id}>
              <h3>{skill.name}</h3>
              <div className="rating-buttons" role="group" aria-label={skill.name}>
                {[0, 1, 2, 3, 4].map((n) => (
                  <button
                    type="button"
                    key={n}
                    aria-label={skill.name + ': ' + n}
                    aria-pressed={form.skills.find((s) => s.skill_id === skill.id)?.value === n}
                    className={
                      form.skills.find((s) => s.skill_id === skill.id)?.value === n
                        ? 'selected'
                        : ''
                    }
                    onClick={() => scoreSkill(skill.id, n)}
                  >
                    {n}
                  </button>
                ))}
                <button
                  type="button"
                  aria-label={skill.name + ': не оценивалось'}
                  aria-pressed={!form.skills.some((s) => s.skill_id === skill.id)}
                  className={
                    !form.skills.some((s) => s.skill_id === skill.id) ? 'selected skip' : 'skip'
                  }
                  onClick={() => scoreSkill(skill.id, null)}
                >
                  —
                </button>
              </div>
            </div>
          ))}
        </section>
        <section className="card stack">
          <h2>Самостоятельность</h2>
          <div className="choice-grid">
            {[
              ['A0', 'Постоянная помощь'],
              ['A1', 'Частые подсказки'],
              ['A2', 'Редкие подсказки'],
              ['A3', 'Самостоятельно'],
            ].map(([code, label]) => (
              <button
                type="button"
                className={'choice ' + (form.autonomy_level.startsWith(code) ? 'selected' : '')}
                aria-pressed={form.autonomy_level.startsWith(code)}
                key={code}
                onClick={() => update({ autonomy_level: code })}
              >
                <strong>{code}</strong>
                {label}
              </button>
            ))}
          </div>
        </section>
        <section className="card stack">
          <h2>Безопасность</h2>
          <div className="chips">
            {['нет', 'словесная подсказка', 'физическое вмешательство'].map((type) => (
              <button
                type="button"
                className={'chip ' + (form.intervention.type === type ? 'selected' : '')}
                aria-pressed={form.intervention.type === type}
                key={type}
                onClick={() =>
                  update({
                    intervention: {
                      ...form.intervention,
                      type,
                      is_critical: type === 'нет' ? false : form.intervention.is_critical,
                    },
                  })
                }
              >
                {type === 'нет'
                  ? 'Без вмешательства'
                  : type === 'словесная подсказка'
                    ? 'Подсказка'
                    : 'Физическое вмешательство'}
              </button>
            ))}
          </div>
          {form.intervention.type !== 'нет' && (
            <>
              <label className="field">
                Причина{form.intervention.type === 'физическое вмешательство' ? ' *' : ''}
                <select
                  required={form.intervention.type === 'физическое вмешательство'}
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
                  <option value="Другое">Другое</option>
                </select>
              </label>
              <label className="row small" style={{ minHeight: 44, cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={form.intervention.is_critical}
                  onChange={(e) =>
                    update({
                      intervention: { ...form.intervention, is_critical: e.target.checked },
                    })
                  }
                  style={{ width: 20, height: 20, accentColor: 'var(--red)' }}
                />
                <AlertTriangle size={17} color="var(--red)" />
                Критическое событие
              </label>
              {form.intervention.is_critical && (
                <label className="field">
                  Что произошло
                  <textarea
                    maxLength={2000}
                    value={form.intervention.description || ''}
                    onChange={(e) =>
                      update({
                        intervention: { ...form.intervention, description: e.target.value },
                      })
                    }
                    placeholder="Кратко опишите ситуацию и ваше вмешательство"
                  />
                </label>
              )}
            </>
          )}
        </section>
        <section className="card stack">
          <h2>Общая оценка занятия</h2>
          <div className="rating-buttons" role="group" aria-label="Общая оценка">
            {[1, 2, 3, 4, 5].map((n) => (
              <button
                type="button"
                key={n}
                className={form.overall_grade_1_5 === n ? 'selected' : ''}
                aria-label={'Общая оценка ' + n}
                aria-pressed={form.overall_grade_1_5 === n}
                onClick={() => update({ overall_grade_1_5: n })}
              >
                {n}
              </button>
            ))}
          </div>
          <p className="small muted">Для истории обучения и бумажной книжки.</p>
        </section>
        <section className="card stack">
          <h2>Коротко о результате</h2>
          <label className="field">
            Вердикт · необязательно
            <select
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
          <label className="field">
            Что требует дальнейшей работы
            <textarea
              maxLength={500}
              value={form.comment_internal || ''}
              onChange={(e) => update({ comment_internal: e.target.value })}
              placeholder="Например: продолжить работу с зеркалами перед перестроением"
            />
          </label>
          <p className="small muted">
            {form.comment_internal?.length || 0}/500 · Видно только школе и инструкторам
          </p>
        </section>
        {requireReason && (
          <label className="field">
            Причина исправления *
            <textarea
              required
              value={reason}
              onChange={(e) => {
                setReason(e.target.value)
                onReason?.(e.target.value)
              }}
              maxLength={1000}
            />
          </label>
        )}
      </fieldset>
      <ErrorBox message={error} />
      <div className="report-actions">
        <button
          className="btn full"
          type="submit"
          disabled={busy || !online || !skills.length || !exercises.length}
        >
          <Check size={17} />
          {busy ? 'Сохраняем оценки…' : submitLabel}
        </button>
        {draftKey && (
          <button
            className="text-btn"
            style={{ justifyContent: 'center', padding: 4 }}
            type="button"
            onClick={() => {
              try {
                sessionStorage.setItem(draftKey, JSON.stringify(form))
                setSaved(true)
              } catch {
                setError('Не удалось сохранить черновик. Оставьте форму открытой.')
              }
            }}
          >
            <Save size={13} />
            {saved ? 'Черновик сохранён в этой сессии' : 'Сохранить черновик'}
          </button>
        )}
        <p className="small muted" style={{ textAlign: 'center', fontSize: 10 }}>
          {requireReason
            ? 'Изменение сохранится в журнале аудита'
            : 'После сохранения скор пересчитается автоматически'}
        </p>
      </div>
    </form>
  )
}
