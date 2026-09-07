# Database Documentation

## Основные таблицы (15)

1. **instructors** — инструкторы
2. **clients** — клиенты
3. **bookings** — записи на занятия
4. **lesson_reports** — отчёты о занятиях
5. **exercise_catalog** — каталог упражнений
6. **lesson_exercises** — связь отчёт-упражнения
7. **skill_catalog** — каталог критериев оценки
8. **skill_assessments** — оценки критериев
9. **interventions** — вмешательства инструктора
10. **score_snapshots** — снимки Score
11. **attention_flags** — флаги внимания
12. **ai_drafts** — черновики ИИ-заключений
13. **final_conclusions** — финальные заключения
14. **audit_logs** — аудит действий
15. **access_grants** — временные окна доступа

## Справочники (5)

- **verdict_catalog** — быстрые вердикты
- **intervention_reason_catalog** — причины вмешательств
- **score_formula_versions** — версии формулы Score

## Связи

- instructors 1:N bookings
- clients 1:N bookings
- bookings 1:1 lesson_reports
- lesson_reports 1:N skill_assessments
- lesson_reports 1:N interventions
- clients 1:N score_snapshots
- clients 1:N attention_flags
