import { test, expect } from '@playwright/test'
import { goto } from './helpers'

test.describe('Render Queue Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.route('http://localhost:8400/api/render**', route =>
      route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }),
    )
    await page.route('http://localhost:8400/api/timelines**', route =>
      route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }),
    )
    await page.route('http://localhost:8400/api/captions/styles', route =>
      route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }),
    )
    await page.route('http://localhost:8400/api/**', route =>
      route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }),
    )
  })

  test('shows render queue heading', async ({ page }) => {
    await goto(page, '/render')
    // "Render Queue" appears in both heading and sidebar link — use first()
    await expect(page.getByText(/render queue/i).first()).toBeVisible()
  })

  test('shows new render button', async ({ page }) => {
    await goto(page, '/render')
    await expect(page.getByRole('button', { name: /new render/i })).toBeVisible()
  })

  test('opens render dialog', async ({ page }) => {
    await goto(page, '/render')
    await page.getByRole('button', { name: /new render/i }).click()
    await expect(page.getByRole('dialog')).toBeVisible()
  })

  test('shows empty state with no jobs', async ({ page }) => {
    await goto(page, '/render')
    await expect(page.getByText(/no render jobs/i)).toBeVisible()
  })
})
