import { test, expect } from '@playwright/test'
import { goto } from './helpers'

const emptyLibrary = { items: [], total: 0, page: 1, page_size: 100 }
const emptyClips = { items: [], total: 0, page: 1, page_size: 200 }

test.describe('App Layout', () => {
  test.beforeEach(async ({ page }) => {
    // Wildcard fallback first (lowest priority — LIFO ordering)
    await page.route('http://localhost:8400/api/**', route =>
      route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }),
    )
    // Specific mocks after (higher priority — LIFO)
    await page.route('http://localhost:8400/api/library**', route =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(emptyLibrary) }),
    )
    // Clips must return paginated shape — array crashes ClipsPage
    await page.route('http://localhost:8400/api/clips**', route =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(emptyClips) }),
    )
  })

  test('sidebar is visible on load', async ({ page }) => {
    await goto(page, '/')
    // Use role-based selectors to avoid substring collisions (e.g. "Library" in "Media Library")
    await expect(page.getByRole('link', { name: 'Library', exact: true })).toBeVisible()
    await expect(page.getByRole('link', { name: 'Clips', exact: true })).toBeVisible()
    await expect(page.getByRole('link', { name: 'Story Builder', exact: true })).toBeVisible()
    await expect(page.getByRole('link', { name: 'Render Queue', exact: true })).toBeVisible()
    await expect(page.getByRole('link', { name: 'Settings', exact: true })).toBeVisible()
  })

  test('sidebar navigation works', async ({ page }) => {
    await goto(page, '/')
    await page.getByRole('link', { name: 'Clips', exact: true }).click()
    await expect(page).toHaveURL(/\/clips/)

    await page.getByRole('link', { name: 'Story Builder', exact: true }).click()
    await expect(page).toHaveURL(/\/stories/)

    await page.getByRole('link', { name: 'Render Queue', exact: true }).click()
    await expect(page).toHaveURL(/\/render/)

    await page.getByRole('link', { name: 'Settings', exact: true }).click()
    await expect(page).toHaveURL(/\/settings/)
  })

  test('root redirects to library', async ({ page }) => {
    await goto(page, '/')
    await expect(page.getByText('Media Library', { exact: true })).toBeVisible()
  })
})
