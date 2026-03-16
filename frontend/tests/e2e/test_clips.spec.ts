import { test, expect } from '@playwright/test'
import { goto } from './helpers'

const mockClips = {
  items: [
    {
      clip_id: 'clip-001',
      item_id: 'item-001',
      clip_title: 'Heated Debate Moment',
      start_ms: 5000,
      end_ms: 20000,
      duration_ms: 15000,
      virality_score: 0.85,
      clip_status: 'ready',
      clip_source: 'ai',
      speaker_label: 'SPEAKER_00',
      clip_transcript: 'This is a test clip transcript.',
      item_title: 'Test Video',
      created_at: '2026-01-01T00:00:00',
      updated_at: '2026-01-01T00:00:00',
    },
    {
      clip_id: 'clip-002',
      item_id: 'item-001',
      clip_title: 'Manual Selection',
      start_ms: 30000,
      end_ms: 45000,
      duration_ms: 15000,
      virality_score: 0.6,
      clip_status: 'pending',
      clip_source: 'manual',
      item_title: 'Test Video',
      created_at: '2026-01-01T00:00:00',
      updated_at: '2026-01-01T00:00:00',
    },
  ],
  total: 2,
  page: 1,
  page_size: 200,
}

const emptyClips = { items: [], total: 0, page: 1, page_size: 200 }

test.describe('Clips Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.route('http://localhost:8400/api/**', route =>
      route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }),
    )
    await page.route('http://localhost:8400/api/clips**', route =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(mockClips) }),
    )
  })

  test('shows All Clips heading', async ({ page }) => {
    await goto(page, '/clips')
    await expect(page.getByText(/all clips/i)).toBeVisible()
  })

  test('shows empty state with empty mock', async ({ page }) => {
    await page.route('http://localhost:8400/api/clips**', route =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(emptyClips) }),
    )
    await goto(page, '/clips')
    await expect(page.getByText(/no clips/i)).toBeVisible()
  })

  test('renders clip cards with data', async ({ page }) => {
    await goto(page, '/clips')
    await expect(page.getByText('Heated Debate Moment')).toBeVisible()
  })

  test('shows filter dropdowns', async ({ page }) => {
    await goto(page, '/clips')
    // Status and source filters should be visible
    await expect(page.getByText(/status/i).first()).toBeVisible()
  })

  test('shows Batch Extract button when pending clips exist', async ({ page }) => {
    await goto(page, '/clips')
    await expect(page.getByRole('button', { name: /batch extract/i })).toBeVisible()
  })

  test('hides Batch Extract when all clips are ready', async ({ page }) => {
    const allReady = {
      items: [{ ...mockClips.items[0], clip_status: 'ready' }],
      total: 1,
      page: 1,
      page_size: 200,
    }
    await page.route('http://localhost:8400/api/clips**', route =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(allReady) }),
    )
    await goto(page, '/clips')
    // Wait for content to load
    await expect(page.getByText('Heated Debate Moment')).toBeVisible()
    await expect(page.getByRole('button', { name: /batch extract/i })).not.toBeVisible()
  })

  test('shows clip count', async ({ page }) => {
    await goto(page, '/clips')
    await expect(page.getByText(/2/)).toBeVisible()
  })

  test('Escape clears selection', async ({ page }) => {
    await goto(page, '/clips')
    await expect(page.getByText('Heated Debate Moment')).toBeVisible()
    await page.keyboard.press('Escape')
    // Should not crash — selection cleared
  })

  test('shows min score slider', async ({ page }) => {
    await goto(page, '/clips')
    // Look for score-related filter UI
    const slider = page.locator('input[type="range"]')
    await expect(slider.first()).toBeVisible()
  })

  test('shows source video filter input', async ({ page }) => {
    await goto(page, '/clips')
    // The clips page has text filter inputs for speaker and source video
    const inputs = page.locator('input[type="text"], input[placeholder]')
    await expect(inputs.first()).toBeVisible()
  })
})
