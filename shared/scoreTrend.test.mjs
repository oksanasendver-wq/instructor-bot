import test from 'node:test'
import assert from 'node:assert/strict'
import { periodStart, schoolDate, selectTrendPoints, trendDelta } from './scoreTrend.ts'

test('four periods use real school calendar dates including month ends', () => {
  assert.equal(periodStart('2026-09-07', '3d'), '2026-09-05')
  assert.equal(periodStart('2026-09-07', '1w'), '2026-09-01')
  assert.equal(periodStart('2026-03-31', '1m'), '2026-02-28')
  assert.equal(periodStart('2026-05-31', '3m'), '2026-02-28')
  assert.equal(schoolDate('2026-09-04T20:00:00Z', 'Asia/Almaty'), '2026-09-05')
})

test('one lesson and its corrections never manufacture a trend', () => {
  const points = selectTrendPoints(
    [
      { booking_id: 1, context: 'city', date: '2026-09-06T10:00:00+05:00', score: 20 },
      { booking_id: 1, context: 'city', date: '2026-09-06T10:00:00+05:00', score: 40 },
    ],
    'city',
    '3d',
    '2026-09-07',
    'Asia/Almaty',
  )
  assert.equal(points.length, 1)
  assert.equal(points[0].score, 40)
  assert.equal(trendDelta(points), null)
})

test('filters periods and contexts; zero remains a real score; future and invalid values are excluded', () => {
  const history = [
    { booking_id: 1, context: 'city', date: '2026-09-04T10:00:00+05:00', score: 40 },
    { booking_id: 2, context: 'city', date: '2026-09-04T20:00:00Z', score: 0 },
    { booking_id: 3, context: 'training_ground', date: '2026-09-06', score: 80 },
    { booking_id: 4, context: 'city', date: '2026-09-08', score: 80 },
    { booking_id: 5, context: 'city', date: 'invalid', score: 80 },
    { booking_id: 6, context: 'city', date: '2026-09-06', score: NaN },
  ]
  const points = selectTrendPoints(history, 'city', '3d', '2026-09-07', 'Asia/Almaty')
  assert.equal(points.length, 1)
  assert.equal(points[0].score, 0)
  assert.equal(selectTrendPoints(history, 'city', '1w', '2026-09-07', 'Asia/Almaty').length, 2)
})

test('negative progress stays negative and different methodologies are not compared', () => {
  const points = [
    { context: 'city', date: '2026-09-05', score: 70, formula_version: 1 },
    { context: 'city', date: '2026-09-06', score: 50, formula_version: 1 },
  ]
  assert.equal(trendDelta(points), -20)
  assert.equal(trendDelta([...points, { ...points[1], score: 80, formula_version: 2 }]), null)
})
