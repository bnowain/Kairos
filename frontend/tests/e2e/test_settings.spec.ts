import { test, expect } from '@playwright/test'
import { goto } from './helpers'

test.describe('Settings Page', () => {
  test.beforeEach(async ({ page }) => {
    // Wildcard fallback registered FIRST (lowest priority — LIFO ordering)
    await page.route('http://localhost:8400/api/**', route =>
      route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }),
    )
    // Specific mocks registered AFTER (highest priority — processed first)
    await page.route('http://localhost:8400/api/health', route =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'ok',
          version: '0.1.0',
          cuda_available: true,
          nvenc_available: true,
        }),
      }),
    )
    await page.route('http://localhost:8400/api/config', route =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          whisper_model: 'large-v3',
          ollama_host: 'http://localhost:11434',
          port: 8400,
          cuda_available: true,
          nvenc_available: true,
          video_encoder: 'h264_nvenc',
          whisper_device: 'cuda',
          whisper_compute: 'float16',
          media_library_root: '/tmp',
          database_path: '/tmp/kairos.db',
        }),
      }),
    )
  })

  test('shows health status', async ({ page }) => {
    await goto(page, '/settings')
    // Health badge shows "ok" — use exact match to avoid strict mode violation
    await expect(page.getByText('ok', { exact: true })).toBeVisible()
  })

  test('shows CUDA status', async ({ page }) => {
    await goto(page, '/settings')
    // "CUDA" label appears in the health section
    await expect(page.getByText('CUDA', { exact: true })).toBeVisible()
  })

  test('shows whisper model', async ({ page }) => {
    await goto(page, '/settings')
    await expect(page.getByText('large-v3', { exact: true })).toBeVisible()
  })
})
