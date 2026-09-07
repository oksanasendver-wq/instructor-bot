import { useEffect, useState } from 'react'
import { HashRouter, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import BookingsPage from './pages/BookingsPage'
import { PeoplePage } from './pages/PeoplePage'
import ClientPage from './pages/ClientPage'
import { AuditPage, CatalogsPage, SettingsPage } from './pages/ToolsPages'
export default function App() {
  const [authenticated, setAuthenticated] = useState(!!localStorage.getItem('admin_token'))
  useEffect(() => {
    const update = () => setAuthenticated(!!localStorage.getItem('admin_token'))
    window.addEventListener('admin-auth-change', update)
    window.addEventListener('storage', update)
    return () => {
      window.removeEventListener('admin-auth-change', update)
      window.removeEventListener('storage', update)
    }
  }, [])
  return (
    <HashRouter>
      <Routes>
        <Route
          path="/login"
          element={authenticated ? <Navigate to="/" replace /> : <LoginPage />}
        />
        {authenticated ? (
          <Route element={<Layout />}>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/bookings" element={<BookingsPage />} />
            <Route path="/clients" element={<PeoplePage kind="clients" />} />
            <Route path="/instructors" element={<PeoplePage kind="instructors" />} />
            <Route path="/clients/:id" element={<ClientPage />} />
            <Route path="/catalogs" element={<CatalogsPage />} />
            <Route path="/audit" element={<AuditPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        ) : (
          <Route path="*" element={<Navigate to="/login" replace />} />
        )}
      </Routes>
    </HashRouter>
  )
}
