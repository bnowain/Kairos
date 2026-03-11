import { Page, expect } from '@playwright/test'

/** Navigate to a page and wait for it to be stable. */
export async function goto(page: Page, path: string) {
  // Use domcontentloaded — networkidle hangs when background API polling is active
  await page.goto(path, { waitUntil: 'domcontentloaded' })
}

/** Wait for a status badge to show a specific text. */
export async function waitForStatus(page: Page, status: string, timeout = 10000) {
  await expect(page.getByText(status, { exact: false })).toBeVisible({ timeout })
}

/** Dismiss any open dialogs. */
export async function dismissDialog(page: Page) {
  const esc = page.keyboard.press('Escape')
  await esc
}
