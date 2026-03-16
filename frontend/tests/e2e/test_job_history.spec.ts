import { test, expect } from '@playwright/test'
import { goto } from './helpers'

const mockJobs = [
  {
    job_id: 'job-001',
    urls: ['https://youtube.com/watch?v=test1'],
    template_id: 'viral_reel',
    aspect_ratio: '9:16',
    job_status: 'done',
    stage_label: 'Complete',
    progress: 100,
    output_path: '/media/renders/output.mp4',
    created_at: '2026-01-01T00:00:00',
    updated_at: '2026-01-01T00:00:00',
  },
  {
    job_id: 'job-002',
    urls: ['https://youtube.com/watch?v=test2'],
    template_id: 'viral_reel',
    aspect_ratio: '9:16',
    job_status: 'error',
    stage_label: 'Download failed',
    progress: 10,
    error_msg: 'Network timeout',
    created_at: '2026-01-02T00:00:00',
    updated_at: '2026-01-02T00:00:00',
  },
]

test.describe('Job History Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.route('http://localhost:8400/api/**', route =>
      route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }),
    )
    await page.route('http://localhost:8400/api/jobs**', route =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(mockJobs) }),
    )
  })

  test('shows Job History heading', async ({ page }) => {
    await goto(page, '/jobs')
    await expect(page.getByText(/job history/i)).toBeVisible()
  })

  test('shows New Job button', async ({ page }) => {
    await goto(page, '/jobs')
    await expect(page.getByRole('link', { name: /new job/i }).or(page.getByRole('button', { name: /new job/i }))).toBeVisible()
  })

  test('shows empty state with no jobs', async ({ page }) => {
    await page.route('http://localhost:8400/api/jobs**', route =>
      route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }),
    )
    await goto(page, '/jobs')
    await expect(page.getByText(/no jobs/i)).toBeVisible()
  })

  test('renders job cards with data', async ({ page }) => {
    await goto(page, '/jobs')
    await expect(page.getByText(/done|complete/i).first()).toBeVisible()
  })

  test('shows error message on failed job', async ({ page }) => {
    await goto(page, '/jobs')
    await expect(page.getByText(/network timeout/i)).toBeVisible()
  })

  test('shows Download on completed job', async ({ page }) => {
    await goto(page, '/jobs')
    await expect(page.getByRole('button', { name: /download/i }).or(page.getByRole('link', { name: /download/i }))).toBeVisible()
  })

  test('shows Retry on failed job', async ({ page }) => {
    await goto(page, '/jobs')
    await expect(page.getByRole('button', { name: /retry/i })).toBeVisible()
  })
})
