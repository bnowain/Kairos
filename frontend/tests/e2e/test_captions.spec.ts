import { test, expect } from '@playwright/test'
import { goto } from './helpers'

const mockStyles = [
  {
    style_id: 'style-001',
    style_name: 'Bold TikTok',
    platform_preset: 'tiktok',
    font_name: 'Impact',
    font_size: 64,
    font_color: '#FFFFFF',
    outline_color: '#000000',
    outline_width: 3,
    shadow: 1,
    animation_type: 'word_highlight',
    position: 'bottom',
    created_at: '2026-01-01T00:00:00',
  },
]

test.describe('Caption Styles Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.route('http://localhost:8400/api/**', route =>
      route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }),
    )
    await page.route('http://localhost:8400/api/captions/styles**', route =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(mockStyles) }),
    )
    await page.route('http://localhost:8400/api/caption*styles**', route =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(mockStyles) }),
    )
  })

  test('shows Caption Styles heading', async ({ page }) => {
    await goto(page, '/captions')
    await expect(page.getByText(/caption styles/i).first()).toBeVisible()
  })

  test('shows New Style button', async ({ page }) => {
    await goto(page, '/captions')
    await expect(page.getByRole('button', { name: /new style/i })).toBeVisible()
  })

  test('shows empty state with no styles', async ({ page }) => {
    await page.route('http://localhost:8400/api/captions/styles**', route =>
      route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }),
    )
    await page.route('http://localhost:8400/api/caption*styles**', route =>
      route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }),
    )
    await goto(page, '/captions')
    await expect(page.getByText(/no caption styles/i)).toBeVisible()
  })

  test('renders style cards with data', async ({ page }) => {
    await goto(page, '/captions')
    await expect(page.getByText('Bold TikTok')).toBeVisible()
  })

  test('shows font name in card', async ({ page }) => {
    await goto(page, '/captions')
    await expect(page.getByText(/impact/i)).toBeVisible()
  })

  test('shows edit button on card', async ({ page }) => {
    await goto(page, '/captions')
    await expect(page.getByRole('button', { name: /edit/i }).first()).toBeVisible()
  })

  test('shows delete button on card', async ({ page }) => {
    await goto(page, '/captions')
    await expect(page.getByRole('button', { name: /delete/i }).first()).toBeVisible()
  })
})
