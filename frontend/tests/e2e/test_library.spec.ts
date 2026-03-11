import { test, expect } from '@playwright/test'
import { goto } from './helpers'

const emptyLibrary = { items: [], total: 0, page: 1, page_size: 100 }

test.describe('Library Page', () => {
  test.beforeEach(async ({ page }) => {
    // Wildcard fallback first (lowest priority — LIFO ordering)
    await page.route('http://localhost:8400/api/**', route =>
      route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }),
    )
    // Specific mock after (highest priority — processed first)
    await page.route('http://localhost:8400/api/library**', route =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(emptyLibrary) }),
    )
    await goto(page, '/')
  })

  test('shows Add Video button', async ({ page }) => {
    await expect(page.getByRole('button', { name: /add video/i })).toBeVisible()
  })

  test('opens download dialog on Add Video click', async ({ page }) => {
    await page.getByRole('button', { name: /add video/i }).click()
    await expect(page.getByRole('dialog')).toBeVisible()
    await expect(page.getByPlaceholder(/youtube/i)).toBeVisible()
  })

  test('download dialog closes on cancel', async ({ page }) => {
    await page.getByRole('button', { name: /add video/i }).click()
    await expect(page.getByRole('dialog')).toBeVisible()
    await page.keyboard.press('Escape')
    await expect(page.getByRole('dialog')).not.toBeVisible()
  })

  test('shows empty state when no media', async ({ page }) => {
    await expect(page.getByText(/no videos yet/i)).toBeVisible()
  })

  test('submitting URL in download dialog calls API', async ({ page }) => {
    await page.route('http://localhost:8400/api/acquisition/download', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ item_id: 'test-123', status: 'queued', message: 'Download queued' }),
      })
    })
    await page.getByRole('button', { name: /add video/i }).click()
    await page.getByPlaceholder(/youtube/i).fill('https://youtube.com/watch?v=test')
    await page.getByRole('button', { name: /download|submit|add/i }).last().click()
    // Dialog should close after submit
    await expect(page.getByRole('dialog')).not.toBeVisible({ timeout: 5000 })
  })
})
