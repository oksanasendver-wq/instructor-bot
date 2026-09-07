import { Component, ReactNode } from 'react'

export class ErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false }
  static getDerivedStateFromError() {
    return { failed: true }
  }
  render() {
    if (!this.state.failed) return this.props.children
    return (
      <main className="stack" style={{ maxWidth: 460, margin: '15vh auto', padding: 24 }}>
        <p className="eyebrow">INSTRUCTOR</p>
        <h1>Не удалось открыть экран</h1>
        <p className="muted">
          Попробуйте загрузить приложение снова. Сохранённые отчёты находятся в истории, черновик
          оценки — в этой вкладке.
        </p>
        <button className="btn" onClick={() => window.location.reload()}>
          Загрузить снова
        </button>
      </main>
    )
  }
}
