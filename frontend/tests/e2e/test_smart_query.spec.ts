import { test, expect } from '@playwright/test'
import { goto } from './helpers'

const mockProfiles = [
  {
    intent_profile_id: 'prof-001',
    intent_name: 'Combative Moments',
    intent_description: 'Find heated debates',
    intent_example_count: 5,
    created_at: '2026-01-01T00:00:00',
    updated_at: '2026-01-01T00:00:00',
  },
]

const mockRecentQueries = [
  {
    query_id: 'sq-001',
    query_text: 'Find emotional moments',
    query_source: 'kairos',
    query_status: 'done',
    query_progress: 100,
    query_result_count: 12,
    created_at: '2026-01-01T00:00:00',
    updated_at: '2026-01-01T00:00:00',
  },
]

test.describe('Smart Query Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.route('http://localhost:8400/api/**', route =>
      route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }),
    )
    await page.route('http://localhost:8400/api/intent-profiles**', route =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(mockProfiles) }),
    )
    await page.route('http://localhost:8400/api/smart-query', route =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(mockRecentQueries) }),
    )
  })

  test('shows Smart Query heading', async ({ page }) => {
    await goto(page, '/smart-query')
    await expect(page.getByText(/smart query/i).first()).toBeVisible()
  })

  test('shows query textarea', async ({ page }) => {
    await goto(page, '/smart-query')
    const textarea = page.locator('textarea')
    await expect(textarea.first()).toBeVisible()
  })

  test('shows Search button', async ({ page }) => {
    await goto(page, '/smart-query')
    await expect(page.getByRole('button', { name: /search/i })).toBeVisible()
  })

  test('Search button disabled with empty input', async ({ page }) => {
    await goto(page, '/smart-query')
    const btn = page.getByRole('button', { name: /search/i })
    await expect(btn).toBeDisabled()
  })

  test('shows Filters toggle', async ({ page }) => {
    await goto(page, '/smart-query')
    await expect(page.getByText(/filter/i).first()).toBeVisible()
  })

  test('shows recent queries section', async ({ page }) => {
    await goto(page, '/smart-query')
    await expect(page.getByText(/recent/i).first()).toBeVisible()
    await expect(page.getByText('Find emotional moments')).toBeVisible()
  })

  test('shows intent profile chips', async ({ page }) => {
    await goto(page, '/smart-query')
    await expect(page.getByText('Combative Moments')).toBeVisible()
  })
})
