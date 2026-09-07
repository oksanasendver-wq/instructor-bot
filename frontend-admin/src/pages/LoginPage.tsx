import { useState } from 'react'
import { Route, ArrowRight, ShieldCheck } from 'lucide-react'
import { adminApi } from '../services/api'
import { ErrorBox } from '../components/UI'
import { errorMessage } from '../../../shared/errors'
export default function LoginPage() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  return (
    <div className="admin-login">
      <div className="login-story">
        <div className="brand">
          <span className="brand-mark">
            <Route size={23} />
          </span>
          INSTRUCTOR
        </div>
        <div>
          <p className="eyebrow">Школа, в которой виден прогресс</p>
          <h1>
            За каждым баллом —<br />
            реальная практика.
          </h1>
          <p>
            Ученики, инструкторы и история обучения.
            <br />В одном рабочем пространстве.
          </p>
          <div className="login-road" aria-hidden="true">
            <Route size={180} strokeWidth={0.6} />
          </div>
        </div>
        <p className="small">Практика вождения · Управление обучением</p>
      </div>
      <div className="login-form">
        <form
          className="stack"
          onSubmit={async (e) => {
            e.preventDefault()
            setBusy(true)
            setError('')
            try {
              await adminApi.login(username, password)
            } catch (e) {
              setError(errorMessage(e))
            } finally {
              setBusy(false)
            }
          }}
        >
          <span className="auth-symbol">
            <ShieldCheck size={30} />
          </span>
          <div>
            <h1>С возвращением</h1>
            <p className="muted small" style={{ marginTop: 12 }}>
              Войдите в пространство администратора школы.
            </p>
          </div>
          <label className="field">
            Логин
            <input
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              placeholder="Ваш логин"
            />
          </label>
          <label className="field">
            Пароль
            <input
              autoComplete="current-password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              placeholder="Введите пароль"
            />
          </label>
          <ErrorBox message={error} />
          <button className="btn full" disabled={busy}>
            {busy ? 'Входим…' : 'Войти в админку'}
            <ArrowRight size={17} />
          </button>
          <p className="small muted">Доступ предоставляется администратору школы.</p>
        </form>
      </div>
    </div>
  )
}
