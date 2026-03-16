import { test, expect } from '@playwright/test'
import { goto } from './helpers'

const mockSources = [
  {
    source_id: 'src-001',
    source_type: 'youtube_channel',
    source_url: 'https://youtube.com/@testchannel',
    source_name: 'Test Channel',
    platform: 'youtube',
    schedule_cron: '0 */6 * * *',
    last_polled_at: null,
    enabled: 1,
    download_quality: 'bestvideo[height<=1080]+bestaudio/best',
    created_at: '2026-01-01T00:00:00',
  },
]

test.describe('Sources Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.route('http://localhost:8400/api/**', route =>
      route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }),
    )
    await page.route('http://localhost:8400/api/acquisition/sources**', route =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(mockSources) }),
    )
  })

  test('shows Sources heading', async ({ page }) => {
    await goto(page, '/sources')
    await expect(page.getByText(/sources/i).first()).toBeVisible()
  })

  test('shows Add Source button', async ({ page }) => {
    await goto(page, '/sources')
    await expect(page.getByRole('button', { name: /add source/i })).toBeVisible()
  })

  test('shows empty state with empty mock', async ({ page }) => {
    await page.route('http://localhost:8400/api/acquisition/sources**', route =>
      route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }),
    )
    await goto(page, '/sources')
    await expect(page.getByText(/no sources configured/i)).toBeVisible()
  })

  test('empty state shows Add Source action button', async ({ page }) => {
    await page.route('http://localhost:8400/api/acquisition/sources**', route =>
      route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }),
    )
    await goto(page, '/sources')
    await expect(page.getByRole('button', { name: /add source/i })).toBeVisible()
  })

  test('renders source rows with data', async ({ page }) => {
    await goto(page, '/sources')
    await expect(page.getByText('Test Channel')).toBeVisible()
  })

  test('shows source platform badge', async ({ page }) => {
    await goto(page, '/sources')
    await expect(page.getByText(/youtube/i).first()).toBeVisible()
  })

  test('opens add source dialog on click', async ({ page }) => {
    await goto(page, '/sources')
    await page.getByRole('button', { name: /add source/i }).click()
    await expect(page.getByRole('dialog')).toBeVisible()
  })

  test('dialog closes on Escape', async ({ page }) => {
    await goto(page, '/sources')
    await page.getByRole('button', { name: /add source/i }).click()
    await expect(page.getByRole('dialog')).toBeVisible()
    await page.keyboard.press('Escape')
    await expect(page.getByRole('dialog')).not.toBeVisible()
  })
})
