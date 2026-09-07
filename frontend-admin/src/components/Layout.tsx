import { NavLink, Outlet, useLocation } from 'react-router-dom'
import {
  CalendarDays,
  Users,
  UserRound,
  LayoutDashboard,
  BookOpen,
  ShieldCheck,
  Settings,
  LogOut,
  Route,
} from 'lucide-react'
import { adminApi } from '../services/api'
const links = [
  { path: '/', label: 'Обзор', icon: LayoutDashboard },
  { path: '/bookings', label: 'Расписание', icon: CalendarDays },
  { path: '/clients', label: 'Ученики', icon: Users },
  { path: '/instructors', label: 'Инструкторы', icon: UserRound },
  { path: '/catalogs', label: 'Справочники', icon: BookOpen },
  { path: '/audit', label: 'Журнал изменений', icon: ShieldCheck },
  { path: '/settings', label: 'Настройки', icon: Settings },
]
export default function Layout() {
  const location = useLocation()
  return (
    <div className="admin-shell">
      <aside className="sidebar">
        <NavLink to="/" className="brand">
          <span className="brand-mark">
            <Route size={23} />
          </span>
          <span>
            INSTRUCTOR<span className="brand-caption">управление практикой</span>
          </span>
        </NavLink>
        <p className="eyebrow" style={{ margin: '38px 12px 14px' }}>
          Рабочее пространство
        </p>
        <nav aria-label="Разделы админки">
          {links.map(({ path, label, icon: Icon }) => (
            <NavLink
              end={path === '/'}
              key={path}
              aria-label={label}
              to={path}
              className={({ isActive }) => (isActive ? 'active' : '')}
            >
              <Icon size={19} />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-foot">
          <div className="row">
            <span className="avatar">
              <ShieldCheck size={20} />
            </span>
            <div>
              <h3>Администратор</h3>
              <p className="small muted">Полный доступ школы</p>
            </div>
          </div>
          <button className="text-btn" onClick={() => adminApi.logout()}>
            <LogOut size={15} />
            Выйти из аккаунта
          </button>
        </div>
      </aside>
      <div className="admin-workspace">
        <header className="admin-top">
          <div className="small muted">
            Школа <span style={{ margin: '0 12px', opacity: 0.5 }}>/</span>
            <span style={{ color: 'var(--ink)' }}>
              {links.find((l) => l.path === location.pathname)?.label || 'Карточка ученика'}
            </span>
          </div>
          <div className="row">
            <button
              className="icon-btn"
              aria-label="Выйти из аккаунта"
              onClick={() => adminApi.logout()}
            >
              <LogOut size={16} />
            </button>
            <span className="badge green">
              <span className="dot" />
              Рабочее пространство
            </span>
            <span
              className="avatar"
              style={{ width: 34, height: 34, borderRadius: 11, fontSize: 11 }}
            >
              АД
            </span>
          </div>
        </header>
        <main className="admin-content">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
