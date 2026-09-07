import { useEffect, useState, useCallback, createContext, useContext } from 'react'
import {
  HashRouter,
  Routes,
  Route,
  Navigate,
  NavLink,
  useLocation,
  useNavigate,
} from 'react-router-dom'
import {
  Home,
  Users,
  Plus,
  AlertTriangle,
  UserRound,
  Route as RouteIcon,
  ArrowRight,
  ShieldCheck,
  WifiOff,
  Sparkles,
} from 'lucide-react'
import TodayPage from './pages/TodayPage'
import ReportPage from './pages/ReportPage'
import ClientProfilePage from './pages/ClientProfilePage'
import { ClientsPage, FlagsPage, AccountPage, ReportsPage } from './pages/DirectoryPages'
import { StatisticsPage, SchoolTimePage, AboutPage } from './pages/AccountPages'
import LessonPage from './pages/LessonPage'
import './auxiliary.css'
import { ErrorBox } from './components/UI'
import { api, InstructorProfile } from './services/api'
import { errorMessage } from '../../shared/errors'
export const InstructorContext = createContext<InstructorProfile | null>(null)
export const useInstructor = () => useContext(InstructorContext)!

function Shell() {
  const location = useLocation()
  const navigate = useNavigate()
  const [online, setOnline] = useState(navigator.onLine)
  const isReport = location.pathname.startsWith('/report/')
  useEffect(() => {
    window.scrollTo(0, 0)
    const tg = window.Telegram?.WebApp
    if (location.pathname !== '/' && !isReport) tg?.BackButton?.show()
    else tg?.BackButton?.hide()
    const back = () => navigate(location.pathname.startsWith('/account/') ? '/account' : '/')
    tg?.BackButton?.onClick(back)
    return () => {
      tg?.BackButton?.offClick(back)
    }
  }, [location.pathname, isReport, navigate])
  useEffect(() => {
    if (isReport || location.pathname !== '/') return
    let active = true
    api
      .getBookings()
      .then((bookings) => {
        const pending = bookings.find(
          (b) => b.status === 'assessment_required' && b.actions.includes('report'),
        )
        if (active && pending) navigate('/report/' + pending.id, { replace: true })
      })
      .catch(() => {
        /* The current page and auth boundary display request errors. */
      })
    return () => {
      active = false
    }
  }, [location.pathname, isReport, navigate])
  useEffect(() => {
    const update = () => setOnline(navigator.onLine)
    window.addEventListener('online', update)
    window.addEventListener('offline', update)
    return () => {
      window.removeEventListener('online', update)
      window.removeEventListener('offline', update)
    }
  }, [])
  return (
    <div className="mini-app">
      {!online && (
        <div className="offline-banner">
          <WifiOff size={13} /> Нет связи. Дождитесь подключения перед сохранением.
        </div>
      )}
      <main className={isReport ? 'mini-main report-main' : 'mini-main'}>
        <Routes>
          <Route path="/" element={<TodayPage />} />
          <Route path="/schedule" element={<TodayPage schedule />} />
          <Route path="/clients" element={<ClientsPage />} />
          <Route path="/flags" element={<FlagsPage />} />
          <Route path="/reports" element={<ReportsPage />} />
          <Route path="/account" element={<AccountPage />} />
          <Route path="/account/statistics" element={<StatisticsPage />} />
          <Route path="/account/time" element={<SchoolTimePage />} />
          <Route path="/account/about" element={<AboutPage />} />
          <Route path="/client/:clientId" element={<ClientProfilePage />} />
          <Route path="/lessons/:bookingId" element={<LessonPage />} />
          <Route path="/report/:bookingId" element={<ReportPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
      {!isReport && (
        <nav className="aurora-dock" aria-label="Основная навигация">
          <NavLink
            end
            to="/"
            className={({ isActive }) => 'aurora-tab ' + (isActive ? 'active' : '')}
          >
            <Home size={20} strokeWidth={2.5} />
            <span className="aurora-tab-text">Главная</span>
          </NavLink>

          <NavLink
            to="/clients"
            className={({ isActive }) => 'aurora-tab ' + (isActive ? 'active' : '')}
          >
            <Users size={20} strokeWidth={2.5} />
            <span className="aurora-tab-text">Ученики</span>
          </NavLink>

          <NavLink to="/schedule" className="aurora-center-btn" aria-label="Расписание">
            <Plus size={24} strokeWidth={3} />
          </NavLink>

          <NavLink
            to="/flags"
            className={({ isActive }) => 'aurora-tab ' + (isActive ? 'active' : '')}
          >
            <AlertTriangle size={20} strokeWidth={2.5} />
            <span className="aurora-tab-text">Риски</span>
          </NavLink>

          <NavLink
            to="/account"
            className={({ isActive }) => 'aurora-tab ' + (isActive ? 'active' : '')}
          >
            <UserRound size={20} strokeWidth={2.5} />
            <span className="aurora-tab-text">Профиль</span>
          </NavLink>
        </nav>
      )}
    </div>
  )
}
function App() {
  const [instructor, setInstructor] = useState<InstructorProfile | null>(null)
  const [state, setState] = useState('loading')
  const [error, setError] = useState('')
  const [contactStatus, setContactStatus] = useState('')
  const authenticate = useCallback(async () => {
    setError('')
    try {
      let init = window.Telegram?.WebApp?.initData
      if (!init && import.meta.env.DEV && import.meta.env.VITE_LOCAL_PREVIEW === 'true') {
        const response = await fetch('/__preview/session')
        if (!response.ok) throw new Error('Local preview unavailable')
        init = (await response.json()).init_data
      }
      if (init) {
        const auth = await api.authenticateTelegram(init)
        api.setToken(auth.access_token)
      } else if (!localStorage.getItem('instructor_token')) {
        setState('telegram')
        return false
      }
      setInstructor(await api.getMe())
      setState('ready')
      return true
    } catch (e) {
      const err = e as { response?: { status?: number; data?: { detail?: string } } }
      if (err.response?.data?.detail === 'Phone confirmation required') {
        setState('contact')
        return false
      }
      if (err.response?.status === 401 || err.response?.status === 404)
        localStorage.removeItem('instructor_token')
      setError(errorMessage(e))
      setState('error')
      return false
    }
  }, [])
  useEffect(() => {
    const tg = window.Telegram?.WebApp
    tg?.ready()
    tg?.expand()
    const theme = () => {
      document.documentElement.dataset.theme = tg?.colorScheme === 'dark' ? 'dark' : 'light'
      if (tg?.isVersionAtLeast?.('6.1')) {
        tg.setHeaderColor?.(tg.colorScheme === 'dark' ? '#0b0f17' : '#f8fafc')
        tg.setBackgroundColor?.(tg.colorScheme === 'dark' ? '#0b0f17' : '#f8fafc')
      }
    }
    theme()
    tg?.onEvent?.('themeChanged', theme)
    authenticate()
    const expired = () => {
      setInstructor(null)
      setState('error')
      setError('Сессия истекла. Откройте приложение снова или повторите вход.')
    }
    const logout = () => {
      setInstructor(null)
      setError('')
      setState('signed-out')
    }
    window.addEventListener('instructor-logout', logout)
    window.addEventListener('instructor-session-expired', expired)
    return () => {
      window.removeEventListener('instructor-logout', logout)
      tg?.offEvent?.('themeChanged', theme)
      window.removeEventListener('instructor-session-expired', expired)
    }
  }, [authenticate])
  const requestContact = () => {
    const tg = window.Telegram?.WebApp
    if (!tg?.requestContact || (tg.isVersionAtLeast && !tg.isVersionAtLeast('6.9'))) {
      setError('Обновите Telegram для подтверждения номера.')
      return
    }
    setContactStatus('Ожидаем подтверждение…')
    tg.requestContact(async (sent) => {
      if (!sent) {
        setContactStatus('Номер не передан. Разрешите отправку контакта.')
        return
      }
      for (let attempt = 0; attempt < 6; attempt++) {
        await new Promise((resolve) => window.setTimeout(resolve, 1200))
        if (await authenticate()) return
      }
      setContactStatus(
        'Проверьте у администратора, что ваш номер добавлен и привязка контакта настроена. Затем нажмите «Проверить снова».',
      )
    })
  }
  if (state === 'ready' && instructor)
    return (
      <InstructorContext.Provider value={instructor}>
        <HashRouter>
          <Shell />
        </HashRouter>
      </InstructorContext.Provider>
    )
  return (
    <div className="auth-page">
      <div className="auth-ambient-orb orb-1" aria-hidden="true" />
      <div className="auth-ambient-orb orb-2" aria-hidden="true" />

      <header className="auth-header">
        <div className="auth-brand-badge">
          <div className="auth-brand-icon">
            <RouteIcon size={20} strokeWidth={2.4} />
          </div>
          <div className="auth-brand-info">
            <span className="auth-brand-title">INSTRUCTOR</span>
            <span className="auth-brand-sub">Практика, которая ведёт вперёд</span>
          </div>
        </div>
        <div className="auth-status-pill">
          <span className="auth-status-dot" />
          <span>MINI APP</span>
        </div>
      </header>

      <main className="auth-card">
        <div className="auth-hero-visual">
          <div className="auth-orb-glow" />
          <div className={`auth-orb-ring ${state === 'loading' ? 'is-spinning' : ''}`} />
          <div className="auth-orb-core">
            {state === 'loading' ? (
              <Sparkles size={32} className="auth-core-icon is-pulsing" />
            ) : state === 'contact' ? (
              <UserRound size={32} className="auth-core-icon" />
            ) : (
              <ShieldCheck size={32} className="auth-core-icon" />
            )}
          </div>
          {state === 'loading' && <div className="auth-radar-wave" />}
        </div>

        <div className="auth-content">
          <div className="auth-eyebrow-pill">
            <Sparkles size={12} />
            <span>РАБОЧЕЕ ПРОСТРАНСТВО ИНСТРУКТОРА</span>
          </div>

          <h1 className="auth-title">
            {state === 'loading'
              ? 'Готовим ваш день'
              : state === 'contact'
                ? 'Давайте знакомиться'
                : state === 'telegram'
                  ? 'Ваш день.\nВаши ученики.'
                  : 'Вернёмся к работе'}
          </h1>

          <p className="auth-desc">
            {state === 'loading'
              ? 'Проверяем доступ и синхронизируем расписание занятий…'
              : state === 'contact'
                ? 'Подтвердите номер телефона. Он должен совпадать с номером, который указал администратор школы.'
                : 'Откройте приложение через кнопку меню бота школы в Telegram. Расписание, история и оценки будут под рукой.'}
          </p>
        </div>

        {state === 'loading' && (
          <div className="auth-loading-tracker">
            <div className="auth-progress-track">
              <div className="auth-progress-fill" />
            </div>
            <div className="auth-loading-step">
              <span className="auth-step-dot" />
              <span>Безопасная синхронизация Telegram…</span>
            </div>
          </div>
        )}

        <ErrorBox message={error} />

        {state === 'contact' && (
          <div className="auth-actions">
            <button className="auth-btn-primary full" onClick={requestContact}>
              <span>Подтвердить номер</span>
              <ArrowRight size={18} />
            </button>
            {contactStatus && (
              <p className="auth-contact-status" aria-live="polite">
                {contactStatus}
              </p>
            )}
            <button className="auth-text-btn" onClick={authenticate}>
              Проверить снова
            </button>
          </div>
        )}

        {(state === 'error' || state === 'signed-out') && (
          <div className="auth-actions">
            <button className="auth-btn-primary full" onClick={authenticate}>
              <span>Повторить вход</span>
              <ArrowRight size={18} />
            </button>
          </div>
        )}

        <div className="auth-foot">
          <ShieldCheck size={14} className="auth-foot-icon" />
          <span>Только для инструкторов вашей автошколы</span>
        </div>
      </main>

      <footer className="auth-footer">
        <p className="auth-footer-tagline">Каждое занятие — понятный следующий шаг</p>
      </footer>
    </div>
  )
}
export default App
