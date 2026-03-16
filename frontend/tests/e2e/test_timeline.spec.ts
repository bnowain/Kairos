import { test, expect } from '@playwright/test'
import { goto } from './helpers'

const mockTimeline = {
  timeline_id: 'tl-001',
  timeline_name: 'My Story',
  story_template: 'viral_reel',
  aspect_ratio: '16:9',
  target_duration_ms: 30000,
  timeline_status: 'ready',
  element_count: 2,
  clip_count: 1,
  elements: [
    {
      element_id: 'el-001',
      timeline_id: 'tl-001',
      element_type: 'clip',
      position: 0,
      start_ms: 0,
      duration_ms: 15000,
      clip_id: 'clip-001',
      created_at: '2026-01-01T00:00:00',
    },
    {
      element_id: 'el-002',
      timeline_id: 'tl-001',
      element_type: 'title_card',
      position: 1,
      start_ms: 15000,
      duration_ms: 3000,
      element_params: '{"text":"Intro"}',
      created_at: '2026-01-01T00:00:00',
    },
  ],
  created_at: '2026-01-01T00:00:00',
  updated_at: '2026-01-01T00:00:00',
}

test.describe('Timeline Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.route('http://localhost:8400/api/**', route =>
      route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }),
    )
    await page.route('http://localhost:8400/api/stories/timelines/tl-001**', route =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(mockTimeline) }),
    )
    await page.route('http://localhost:8400/api/timelines/tl-001**', route =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(mockTimeline) }),
    )
    await page.route('http://localhost:8400/api/clips**', route =>
      route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }),
    )
    await page.route('http://localhost:8400/api/captions/styles**', route =>
      route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }),
    )
  })

  test('shows timeline name in header', async ({ page }) => {
    await goto(page, '/timeline/tl-001')
    await expect(page.getByText('My Story')).toBeVisible()
  })

  test('shows aspect ratio badge', async ({ page }) => {
    await goto(page, '/timeline/tl-001')
    await expect(page.getByText('16:9')).toBeVisible()
  })

  test('shows Preview button', async ({ page }) => {
    await goto(page, '/timeline/tl-001')
    await expect(page.getByRole('button', { name: /preview/i })).toBeVisible()
  })

  test('shows Render button', async ({ page }) => {
    await goto(page, '/timeline/tl-001')
    await expect(page.getByRole('button', { name: /render/i }).or(page.getByRole('link', { name: /render/i }))).toBeVisible()
  })
})
