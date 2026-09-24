import { expect, test } from '@playwright/test';

test('Arabic is the default locale and the page is RTL', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('html')).toHaveAttribute('lang', 'ar');
  await expect(page.locator('html')).toHaveAttribute('dir', 'rtl');
  await expect(page.getByRole('heading', { level: 1 })).toHaveText(
    'سوق السيارات المستعملة الموثوق',
  );
});

test('user can switch to English (LTR) and back', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('link', { name: 'اللغة' }).click();
  await expect(page).toHaveURL(/\/en$/);
  await expect(page.locator('html')).toHaveAttribute('dir', 'ltr');
  await expect(page.getByRole('heading', { level: 1 })).toHaveText(
    'The trusted used-car marketplace',
  );

  await page.getByRole('link', { name: 'Language' }).click();
  await expect(page.locator('html')).toHaveAttribute('dir', 'rtl');
});

test('search filters are available without signing in', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByLabel('الماركة')).toBeVisible();
  await expect(page.getByLabel('المدينة')).toBeVisible();
  await expect(page.getByTestId('results-count')).toBeVisible();
});

test('page has no horizontal overflow at phone width', async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 740 });
  await page.goto('/');
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
  );
  expect(overflow).toBe(false);
});
