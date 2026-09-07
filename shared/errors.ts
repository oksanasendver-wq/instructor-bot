export function errorMessage(error: unknown): string {
  const e = error as { response?: { status?: number; data?: { detail?: unknown } }; code?: string }
  const detail = e?.response?.data?.detail
  if (Array.isArray(detail))
    return detail
      .map((d: { msg?: string }) => (d.msg || 'Проверьте данные').replace('Value error, ', ''))
      .join('. ')
  if (typeof detail === 'string') {
    const translated: Record<string, string> = {
      'Invalid credentials': 'Неверный логин или пароль',
      'Phone confirmation required': 'Подтвердите номер телефона',
      'Instructor not found or not active':
        'Доступ инструктора отключён. Обратитесь к администратору',
      'Invalid or expired token': 'Сессия истекла. Войдите снова',
    }
    return translated[detail] || detail
  }
  if (!e?.response) return 'Нет связи с сервером. Проверьте интернет и повторите попытку.'
  return 'Не удалось выполнить действие. Повторите попытку.'
}
