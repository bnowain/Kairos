import { test, expect } from '@playwright/test'
import { goto } from './helpers'

const mockTemplates = [
  {
    template_id: 'viral_reel',
    name: 'Viral Reel',
    description: 'Short-form vertical clip',
    pacing: 'fast',
    target_duration_ms: 60000,
    aspect_ratio_default: '9:16',
  },
]

test.describe('Quick Job Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.route('http://localhost:8400/api/**', route =>
      route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }),
    )
    await page.route('http://localhost:8400/api/stories/templates**', route =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(mockTemplates) }),
    )
    await page.route('http://localhost:8400/api/stories**', route =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(mockTemplates) }),
    )
    await page.route('http://localhost:8400/api/caption*styles**', route =>
      route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }),
    )
    await page.route('http://localhost:8400/api/captions/styles**', route =>
      route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }),
    )
  })

  test('shows Quick Job heading', async ({ page }) => {
    await goto(page, '/quick')
    await expect(page.getByText(/quick job/i).first()).toBeVisible()
  })

  test('shows URL input', async ({ page }) => {
    await goto(page, '/quick')
    const input = page.locator('input[type="text"], input[type="url"], input[placeholder*="http"], input[placeholder*="URL"], input[placeholder*="url"]')
    await expect(input.first()).toBeVisible()
  })

  test('shows Add another URL link', async ({ page }) => {
    await goto(page, '/quick')
    await expect(page.getByText(/add another|add url/i)).toBeVisible()
  })

  test('shows template list', async ({ page }) => {
    await goto(page, '/quick')
    await expect(page.getByText(/viral reel/i)).toBeVisible()
  })

  test('shows aspect ratio options', async ({ page }) => {
    await goto(page, '/quick')
    await expect(page.getByText('9:16')).toBeVisible()
    await expect(page.getByText('16:9')).toBeVisible()
    await expect(page.getByText('1:1')).toBeVisible()
  })

  test('shows TikTok / Reels sub-label for 9:16', async ({ page }) => {
    await goto(page, '/quick')
    await expect(page.getByText(/tiktok|reels/i).first()).toBeVisible()
  })

  test('shows Generate button', async ({ page }) => {
    await goto(page, '/quick')
    await expect(page.getByRole('button', { name: /generate/i })).toBeVisible()
  })
})
