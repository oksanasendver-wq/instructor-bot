import { useState } from 'react'
import { Plus, PenLine, ShieldCheck, Settings, Check, BookOpen } from 'lucide-react'
import { adminApi } from '../services/api'
import { Empty, ErrorBox, Loading, Modal, useResource } from '../components/UI'
import { CatalogItem, dateLabel } from '../../../shared/types'
import { errorMessage } from '../../../shared/errors'
export function CatalogsPage() {
  const [kind, setKind] = useState('exercises'),
    [context, setContext] = useState('Учебная площадка'),
    [editing, setEditing] = useState<CatalogItem | true | null>(null)
  const { data, error, loading, reload } = useResource(
    () => adminApi.get<CatalogItem[]>('/catalogs/' + kind, kind === 'verdicts' ? {} : { context }),
    kind + context,
  )
  return (
    <div className="stack">
      <div className="admin-heading">
        <div>
          <p className="eyebrow">Единый язык обучения</p>
          <h1>Справочники</h1>
          <p className="small muted">
            Упражнения, критерии и формулировки, которые видит инструктор.
          </p>
        </div>
        <button className="btn" onClick={() => setEditing(true)}>
          <Plus size={17} />
          Добавить
        </button>
      </div>
      <div className="table-tools">
        <div className="tabs">
          {[
            ['exercises', 'Упражнения'],
            ['skills', 'Критерии'],
            ['verdicts', 'Вердикты'],
            ['reasons', 'Вмешательства'],
          ].map(([k, label]) => (
            <button key={k} className={kind === k ? 'active' : ''} onClick={() => setKind(k)}>
              {label}
            </button>
          ))}
        </div>
        {kind !== 'verdicts' && (
          <select
            className="input"
            style={{ maxWidth: 210 }}
            aria-label="Контекст справочника"
            value={context}
            onChange={(e) => setContext(e.target.value)}
          >
            <option>Учебная площадка</option>
            <option>Город</option>
          </select>
        )}
      </div>
      <ErrorBox message={error} retry={reload} />
      {kind === 'skills' && (
        <div className="alert info">
          <ShieldCheck size={18} />
          Изменение критерия создаёт новую версию формулы. Исторические снимки оценок сохраняются.
        </div>
      )}
      {loading ? (
        <Loading />
      ) : (
        <div className="card table-card">
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Название</th>
                  <th>{kind === 'skills' ? 'Вес / версия' : 'Раздел / контекст'}</th>
                  <th>Статус</th>
                  <th>Действия</th>
                </tr>
              </thead>
              <tbody>
                {data?.map((item) => (
                  <tr key={item.id}>
                    <td>
                      <strong>{item.short_name || item.name}</strong>
                      {item.official_name && <p className="small muted">{item.official_name}</p>}
                    </td>
                    <td>
                      {kind === 'skills' ? (
                        <span>
                          {item.weight}% · v{item.version}
                          {item.is_core ? ' · ключевой' : ''}
                        </span>
                      ) : (
                        <span className="small muted">
                          {item.paper_section || item.context || 'Все занятия'}
                        </span>
                      )}
                    </td>
                    <td>
                      <span className={'badge ' + (item.active ? 'green' : '')}>
                        {item.active ? 'Используется' : 'Отключён'}
                      </span>
                    </td>
                    <td>
                      <button
                        className="icon-btn"
                        onClick={() => setEditing(item)}
                        aria-label={'Изменить ' + (item.short_name || item.name)}
                      >
                        <PenLine size={15} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!data?.length && (
              <Empty
                title="Справочник пуст"
                text="Добавьте первый элемент, чтобы он появился у инструкторов."
              />
            )}
          </div>
        </div>
      )}
      {editing && (
        <Modal
          title={editing === true ? 'Новый элемент' : 'Изменить элемент'}
          onClose={() => setEditing(null)}
        >
          <CatalogForm
            kind={kind}
            context={context}
            item={editing === true ? undefined : editing}
            onSaved={() => {
              setEditing(null)
              reload()
            }}
          />
        </Modal>
      )}
    </div>
  )
}
function CatalogForm({
  kind,
  context,
  item,
  onSaved,
}: {
  kind: string
  context: string
  item?: CatalogItem
  onSaved: () => void
}) {
  const [form, setForm] = useState({
    context,
    name: item?.name || '',
    short_name: item?.short_name || '',
    official_name: item?.official_name || '',
    paper_section: item?.paper_section || '',
    weight: item?.weight || 10,
    is_core: item?.is_core || false,
    sort_order: item?.sort_order || 0,
    active: item?.active ?? true,
    reason: '',
  })
  const [busy, setBusy] = useState(false),
    [error, setError] = useState('')
  const update = (key: string, value: unknown) => setForm((f) => ({ ...f, [key]: value }))
  return (
    <form
      className="stack"
      onSubmit={async (e) => {
        e.preventDefault()
        setBusy(true)
        try {
          if (item) await adminApi.patch('/catalogs/' + kind + '/' + item.id, form)
          else await adminApi.post('/catalogs/' + kind, form)
          onSaved()
        } catch (e) {
          setError(errorMessage(e))
        } finally {
          setBusy(false)
        }
      }}
    >
      {kind === 'exercises' ? (
        <>
          <label className="field">
            Короткое название *
            <input
              required
              maxLength={100}
              value={form.short_name}
              onChange={(e) => update('short_name', e.target.value)}
            />
          </label>
          <label className="field">
            Полное название для истории *
            <textarea
              required
              maxLength={500}
              value={form.official_name}
              onChange={(e) => update('official_name', e.target.value)}
            />
          </label>
          <label className="field">
            Раздел бумажной книжки
            <input
              maxLength={255}
              value={form.paper_section}
              onChange={(e) => update('paper_section', e.target.value)}
            />
          </label>
        </>
      ) : (
        <label className="field">
          Название *
          <input
            required
            maxLength={255}
            value={form.name}
            onChange={(e) => update('name', e.target.value)}
          />
        </label>
      )}
      {kind === 'skills' && (
        <>
          <label className="field">
            Вес критерия, %
            <input
              required
              type="number"
              step=".01"
              min=".01"
              max={100}
              value={form.weight}
              onChange={(e) => update('weight', Number(e.target.value))}
            />
          </label>
          <label className="row small">
            <input
              type="checkbox"
              checked={form.is_core}
              onChange={(e) => update('is_core', e.target.checked)}
            />
            Ключевой критерий
          </label>
        </>
      )}
      <label className="field">
        Порядок в списке
        <input
          type="number"
          min={0}
          max={1000}
          value={form.sort_order}
          onChange={(e) => update('sort_order', Number(e.target.value))}
        />
      </label>
      <label className="row small">
        <input
          type="checkbox"
          checked={form.active}
          onChange={(e) => update('active', e.target.checked)}
        />
        Использовать в новых отчётах
      </label>
      <label className="field">
        Причина изменения *
        <input
          required
          minLength={3}
          maxLength={1000}
          value={form.reason}
          onChange={(e) => update('reason', e.target.value)}
          placeholder="Например: уточнение названия упражнения"
        />
      </label>
      <ErrorBox message={error} />
      <button className="btn full" disabled={busy}>
        <Check size={16} />
        {busy ? 'Сохраняем…' : 'Сохранить'}
      </button>
    </form>
  )
}
type Audit = {
  id: number
  actor_type: string
  actor_id: number
  entity_type: string
  entity_id: number
  action: string
  old: unknown
  new: unknown
  reason: string
  created_at: string
}
export function AuditPage() {
  const [entity, setEntity] = useState(''),
    [selected, setSelected] = useState<Audit | null>(null)
  const { data, error, loading, reload } = useResource(
    () => adminApi.get<Audit[]>('/audit', entity ? { entity_type: entity } : {}),
    entity,
  )
  const names: Record<string, string> = {
    report: 'Отчёт',
    booking: 'Занятие',
    client: 'Ученик',
    instructor: 'Инструктор',
    conclusion: 'Заключение',
    ai_draft: 'ИИ-черновик',
    attention_flag: 'Флаг внимания',
    skills: 'Критерий',
    exercises: 'Упражнение',
  }
  const actions: Record<string, string> = {
    create: 'Создание',
    update: 'Изменение',
    correct: 'Исправление',
    delete: 'Удаление / архив',
    deactivate: 'Архивация',
    grant_access: 'Повторный доступ',
    approve: 'Утверждение',
    arrived: 'Приход',
    finish: 'Завершение',
    payment: 'Оплата',
    'no-show': 'Неявка',
    open: 'Открыт флаг',
    close: 'Закрыт флаг',
    access_expired: 'Истёк доступ',
    generate: 'Генерация',
    before_update: 'До исправления',
  }
  return (
    <div className="stack">
      <div className="admin-heading">
        <div>
          <p className="eyebrow">История решений школы</p>
          <h1>Журнал изменений</h1>
          <p className="small muted">Кто, когда и почему изменил данные. Последние 100 событий.</p>
        </div>
        <select
          className="input"
          style={{ maxWidth: 230 }}
          aria-label="Тип события"
          value={entity}
          onChange={(e) => setEntity(e.target.value)}
        >
          <option value="">Все сущности</option>
          {Object.entries(names).map(([key, label]) => (
            <option key={key} value={key}>
              {label}
            </option>
          ))}
        </select>
      </div>
      <ErrorBox message={error} retry={reload} />
      {loading ? (
        <Loading />
      ) : (
        <div className="card table-card">
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Когда</th>
                  <th>Кто</th>
                  <th>Что изменилось</th>
                  <th>Причина</th>
                  <th>Детали</th>
                </tr>
              </thead>
              <tbody>
                {data?.map((a) => (
                  <tr key={a.id}>
                    <td>
                      {dateLabel(a.created_at, {
                        day: 'numeric',
                        month: 'short',
                        hour: '2-digit',
                        minute: '2-digit',
                        timeZone: 'Asia/Almaty',
                      })}
                    </td>
                    <td>
                      {a.actor_type === 'admin'
                        ? 'Администратор'
                        : a.actor_type === 'system'
                          ? 'Система'
                          : 'Инструктор #' + a.actor_id}
                    </td>
                    <td>
                      <strong>
                        {names[a.entity_type] || a.entity_type} #{a.entity_id}
                      </strong>
                      <p className="small muted">{actions[a.action] || a.action}</p>
                    </td>
                    <td className="small muted">{a.reason || '—'}</td>
                    <td>
                      <button className="text-btn" onClick={() => setSelected(a)}>
                        Сравнить
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {!data?.length && (
            <Empty
              title="Изменений пока нет"
              text="События появятся после первых действий в системе."
            />
          )}
        </div>
      )}
      {selected && (
        <Modal title="Детали изменения" onClose={() => setSelected(null)}>
          <p className="small muted">{selected.reason || 'Изменение данных'}</p>
          <h3>До изменения</h3>
          <pre className="audit-json">{JSON.stringify(selected.old, null, 2) || '—'}</pre>
          <h3>После изменения</h3>
          <pre className="audit-json">{JSON.stringify(selected.new, null, 2) || '—'}</pre>
        </Modal>
      )}
    </div>
  )
}
type SchoolMethodology = {
  version: number
  valid_from: string
  recency_weights: number[]
  ground_weights: Record<string, CatalogItem | number>
  city_weights: Record<string, CatalogItem | number>
  overall_weights: Record<string, number>
  caps: {
    autonomy?: Record<string, number>
    physical?: number
    critical?: number
    repeated_physical?: number
    overall_critical_last_10?: number
  }
}
export function SettingsPage() {
  const { data, error, loading, reload } = useResource(() =>
    adminApi.get<{
      timezone: string
      ai_provider: string
      ai_model: string
      ai_configured: boolean
      webhook_configured: boolean
      instruction: string
      access_policy: {
        arrival_minutes_before: number
        profile_minutes_after: number
        edit_minutes_after: number
      }
      score_methodology: SchoolMethodology | null
    }>('/settings'),
  )
  return (
    <div className="stack">
      <div className="admin-heading">
        <div>
          <p className="eyebrow">Подключения и правила</p>
          <h1>Настройки школы</h1>
          <p className="small muted">Состояние Telegram, ИИ-помощника и временных правил.</p>
        </div>
      </div>
      <ErrorBox message={error} retry={reload} />
      {loading ? (
        <Loading />
      ) : (
        data && (
          <div className="dashboard-grid">
            <section className="card stack">
              <div className="row">
                <Settings size={21} color="var(--blue)" />
                <h2>ИИ-помощник</h2>
              </div>
              <span className={'badge ' + (data.ai_configured ? 'green' : 'amber')}>
                {data.ai_configured ? 'Ключ настроен' : 'Нужен ключ провайдера'}
              </span>
              <p className="small">
                Провайдер: {data.ai_provider}
                <br />
                Модель: {data.ai_model}
              </p>
              <p className="small muted">{data.instruction}</p>
              <div className="alert info">
                ИИ создаёт только черновик текста. Оценки и итоговое решение остаются за школой.
              </div>
            </section>
            <section className="card stack">
              <div className="row">
                <ShieldCheck size={21} color="var(--green)" />
                <h2>Доступ и время</h2>
              </div>
              <p className="small">Часовой пояс: {data.timezone}</p>
              <p className="small">
                Подтверждение контакта Telegram:{' '}
                {data.webhook_configured ? 'настроен секрет webhook' : 'требуется секрет webhook'}
              </p>
              {data.access_policy ? (
                <dl className="lesson-facts">
                  <div>
                    <dt>Подтверждение прихода</dt>
                    <dd>за {data.access_policy.arrival_minutes_before} мин до начала</dd>
                  </div>
                  <div>
                    <dt>Доступ к карточке</dt>
                    <dd>до {data.access_policy.profile_minutes_after} мин после занятия</dd>
                  </div>
                  <div>
                    <dt>Исправление отчёта</dt>
                    <dd>{data.access_policy.edit_minutes_after} мин после сохранения</dd>
                  </div>
                </dl>
              ) : (
                <p className="small muted">Сервер не передал правила доступа.</p>
              )}
            </section>
            <section className="card stack">
              <div className="row">
                <BookOpen size={21} />
                <h2>Правила расчёта</h2>
              </div>
              {data.score_methodology ? (
                <MethodologyDetails methodology={data.score_methodology} timezone={data.timezone} />
              ) : (
                <p className="small muted">Версия методики ещё не зарегистрирована.</p>
              )}
            </section>
          </div>
        )
      )}
    </div>
  )
}
function MethodologyDetails({
  methodology,
  timezone,
}: {
  methodology: SchoolMethodology
  timezone: string
}) {
  const capLabels = {
    physical: 'Физическое вмешательство',
    critical: 'Критическое событие',
    repeated_physical: 'Повторное физическое вмешательство',
    overall_critical_last_10: 'Общая оценка после критического события в последних десяти занятиях',
  } as const
  return (
    <div className="stack">
      <p className="small">
        Версия {methodology.version} · действует с{' '}
        {dateLabel(methodology.valid_from, {
          day: 'numeric',
          month: 'long',
          year: 'numeric',
          timeZone: timezone,
        })}
      </p>
      {!!methodology.recency_weights?.length && (
        <p className="small muted">
          Вес последних оценок навыка, начиная с самой новой:{' '}
          {methodology.recency_weights.map((weight) => Math.round(weight * 100) + '%').join(', ')}.
          Пропущенные оценки не считаются нулевыми.
        </p>
      )}
      <dl className="lesson-facts">
        {Object.entries(methodology.overall_weights).map(([context, weight]) => (
          <div key={context}>
            <dt>
              Доля{' '}
              {context === 'training_ground' ? 'площадки' : context === 'city' ? 'города' : context}
            </dt>
            <dd>{Math.round(weight * 100)}%</dd>
          </div>
        ))}
      </dl>
      <h3>Ограничения результата</h3>
      <dl className="lesson-facts">
        {Object.entries(methodology.caps.autonomy || {}).map(([level, cap]) => (
          <div key={level}>
            <dt>Самостоятельность {level}</dt>
            <dd>до {cap} баллов</dd>
          </div>
        ))}
        {Object.entries(capLabels).map(([key, label]) => {
          const value = methodology.caps[key as keyof typeof capLabels]
          return value == null ? null : (
            <div key={key}>
              <dt>{label}</dt>
              <dd>до {value} баллов</dd>
            </div>
          )
        })}
      </dl>
      {(
        [
          ['Площадка', methodology.ground_weights],
          ['Город', methodology.city_weights],
        ] as const
      ).map(([label, criteria]) => (
        <details className="methodology-criteria" key={label}>
          <summary>{label}: критерии и веса</summary>
          {Object.keys(criteria).length ? (
            <table>
              <thead>
                <tr>
                  <th>Критерий</th>
                  <th>Вес</th>
                  <th>Версия</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(criteria).map(([id, entry]) => {
                  const criterion: Partial<CatalogItem> =
                    typeof entry === 'number' ? { weight: entry } : entry
                  return (
                    <tr key={id}>
                      <td>
                        {criterion.name || 'Критерий №' + id}
                        {criterion.is_core && <p className="small muted">Ключевой</p>}
                      </td>
                      <td>{criterion.weight == null ? 'Не указан' : criterion.weight}</td>
                      <td>{criterion.version ?? 'Не указана'}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          ) : (
            <p className="small muted">В этой версии критерии не указаны.</p>
          )}
        </details>
      ))}
      <p className="small muted">
        Версия методики сохраняется с каждой оценкой. Изменения критериев доступны в справочнике и
        фиксируются в журнале школы.
      </p>
    </div>
  )
}
