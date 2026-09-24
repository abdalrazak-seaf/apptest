import { expect, test } from '@playwright/test';

test('Arabic is the default locale and the page is RTL', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('html')).toHaveAttribute('lang', 'ar');
  await expect(page.locator('html')).toHaveAttribute('dir', 'rtl');
  await expect(page.getByRole('heading', { level: 1 })).toHaveText(
    'سوق السيارات المستعملة الموثوق',
  );
});

test('placeholder calls the API health endpoint', async ({ page }) => {
  await page.goto('/');
  const status = page.getByTestId('health-status');
  await expect(status).toHaveAttribute('data-state', 'ok');
  await expect(status).toHaveText('الخادم يعمل');
});

test('user can switch to English (LTR) and back', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('link', { name: 'اللغة' }).click();
  await expect(page).toHaveURL(/\/en$/);
  await expect(page.locator('html')).toHaveAttribute('dir', 'ltr');
  await expect(page.getByTestId('health-status')).toHaveText('Server is up');

  await page.getByRole('link', { name: 'Language' }).click();
  await expect(page.locator('html')).toHaveAttribute('dir', 'rtl');
});

test('page has no horizontal overflow at phone width', async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 740 });
  await page.goto('/');
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
  );
  expect(overflow).toBe(false);
});
