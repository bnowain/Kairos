import { test, expect } from '@playwright/test'
import { goto } from './helpers'

test.describe('Item Detail Page', () => {
  // Mock a media item
  const mockItem = {
    item_id: 'mock-item-001',
    platform: 'youtube',
    platform_video_id: 'abc123',
    item_title: 'Mock Test Video',
    item_channel: 'Test Channel',
    item_description: 'A test video description',
    published_at: '2026-01-01T00:00:00',
    duration_seconds: 300,
    original_url: 'https://youtube.com/watch?v=abc123',
    file_path: null,
    audio_path: null,
    thumb_path: null,
    item_status: 'ready',
    error_msg: null,
    has_captions: 0,
    caption_source: null,
    created_at: '2026-01-01T00:00:00',
    updated_at: '2026-01-01T00:00:00',
    transcription_job_status: null,
    segment_count: 0,
    clip_count: 0,
  }

  test.beforeEach(async ({ page }) => {
    await page.route('http://localhost:8400/api/library/mock-item-001', route =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(mockItem) }),
    )
    await page.route('http://localhost:8400/api/transcription/segments/mock-item-001', route =>
      route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }),
    )
    await page.route('http://localhost:8400/api/transcription/jobs**', route =>
      route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }),
    )
    await page.route('http://localhost:8400/api/analysis/mock-item-001/highlights', route =>
      route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }),
    )
    await page.route('http://localhost:8400/api/analysis/mock-item-001/scores', route =>
      route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }),
    )
    await page.route('http://localhost:8400/api/clips**', route =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ items: [], total: 0, page: 1, page_size: 200 }),
      }),
    )
  })

  test('shows item title and metadata', async ({ page }) => {
    await goto(page, '/item/mock-item-001')
    await expect(page.getByText('Mock Test Video')).toBeVisible()
    await expect(page.getByText('Test Channel').first()).toBeVisible()
  })

  test('shows overview tab by default', async ({ page }) => {
    await goto(page, '/item/mock-item-001')
    await expect(page.getByText(/overview/i)).toBeVisible()
  })

  test('can switch to transcript tab', async ({ page }) => {
    await goto(page, '/item/mock-item-001')
    await page.getByRole('tab', { name: /transcript/i }).click()
    await expect(page.getByText(/no transcript yet/i)).toBeVisible()
  })

  test('can switch to analysis tab', async ({ page }) => {
    await goto(page, '/item/mock-item-001')
    await page.getByRole('tab', { name: /analysis/i }).click()
    await expect(page.locator('body')).toBeVisible()
  })

  test('shows back navigation button', async ({ page }) => {
    await goto(page, '/item/mock-item-001')
    const back = page.getByRole('button', { name: /back/i })
      .or(page.getByRole('link', { name: /back|library/i }))
      .or(page.locator('[aria-label="Back to library"]'))
    await expect(back).toBeVisible()
  })
})
