import { test, expect } from '@playwright/test'
import { goto } from './helpers'

const mockTemplates = [
  {
    template_id: 'viral_reel',
    template_name: 'Viral Reel',
    description: 'Strongest moments first',
    pacing: 'fast',
    target_duration_ms: 60000,
    aspect_ratio_default: '9:16',
  },
  {
    template_id: 'political_campaign',
    template_name: 'Political Campaign',
    description: 'Claim, evidence, close',
    pacing: 'moderate',
    target_duration_ms: 120000,
    aspect_ratio_default: '16:9',
  },
]

test.describe('Story Builder Page', () => {
  test.beforeEach(async ({ page }) => {
    // Wildcard fallback first (lowest priority)
    await page.route('http://localhost:8400/api/**', route =>
      route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }),
    )
    // Library must return paginated shape (StoryPage calls fetchLibrary)
    await page.route('http://localhost:8400/api/library**', route =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ items: [], total: 0, page: 1, page_size: 100 }),
      }),
    )
    // Specific mock after (highest priority — LIFO)
    await page.route('http://localhost:8400/api/stories/templates', route =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(mockTemplates) }),
    )
  })

  test('shows template list', async ({ page }) => {
    await goto(page, '/stories')
    await expect(page.getByText('Viral Reel')).toBeVisible()
    await expect(page.getByText('Political Campaign')).toBeVisible()
  })

  test('shows story name input', async ({ page }) => {
    await goto(page, '/stories')
    await expect(page.getByPlaceholder(/untitled story/i)).toBeVisible()
  })

  test('generate button is present', async ({ page }) => {
    await goto(page, '/stories')
    await expect(page.getByRole('button', { name: /generate/i })).toBeVisible()
  })
})
