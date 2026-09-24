/**
 * The Phase 1 happy path: a seller posts a car, an admin approves it, and a buyer finds it
 * by searching in Arabic.
 */
import { expect, test, type APIRequestContext, type Page } from '@playwright/test';

import { ADMIN_PHONE } from '../playwright.config';

const API = `http://localhost:${process.env.E2E_API_PORT ?? 8100}`;

/** A distinct mobile number per run, so repeated runs never collide. */
function uniquePhone(): string {
  return `05${String(Date.now()).slice(-8)}`;
}

/** The smallest valid PNG, used as a car photo. */
const PNG = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==',
  'base64',
);

async function logIn(page: Page, phone: string): Promise<void> {
  await page.goto('/login');
  await page.getByLabel('رقم الجوال').fill(phone);
  await page.getByRole('button', { name: 'أرسل الرمز' }).click();

  // In this environment the API returns the code, and the page shows it.
  const hint = page.getByText(/رمز التطوير/);
  await expect(hint).toBeVisible();
  const code = (await hint.textContent())?.match(/(\d{4,8})/)?.[1];
  expect(code).toBeTruthy();

  await page.getByLabel('رمز التحقق').fill(code!);
  await page.getByRole('button', { name: 'تأكيد' }).click();
  await expect(page.getByRole('button', { name: 'تسجيل الخروج' })).toBeVisible();
}

/** Logs in through the API and returns an access token. */
async function apiToken(request: APIRequestContext, phone: string): Promise<string> {
  const requested = await request.post(`${API}/auth/otp/request`, { data: { phone } });
  const { debug_code: code } = await requested.json();
  const verified = await request.post(`${API}/auth/otp/verify`, {
    data: { phone, code },
  });
  const { access_token: token } = await verified.json();
  return token;
}

test('a seller posts a car, an admin approves it, and a buyer finds it', async ({
  page,
  request,
}) => {
  const sellerPhone = uniquePhone();

  await test.step('the seller signs in', async () => {
    await logIn(page, sellerPhone);
  });

  await test.step('and fills in the car details', async () => {
    await page.getByRole('link', { name: 'أضف سيارتك' }).click();
    await expect(page.getByRole('heading', { name: 'أضف سيارتك' })).toBeVisible();

    await page.getByLabel('الماركة').selectOption({ label: 'جي إم سي' });
    await page.getByLabel('الموديل').selectOption({ label: 'يوكن' });
    // Arabic-Indic digits must be accepted exactly as a Saudi seller types them.
    await page.getByLabel('سنة الصنع').fill('٢٠١٩');
    await page.getByLabel('الممشى بالكيلومترات').fill('٨٥٠٠٠');
    await page.getByLabel('السعر المطلوب بالريال').fill('٩٠٠٠٠');
    await page.getByLabel('أقل سعر تقبله (خاص بك)').fill('٨٢٠٠٠');
    await page.getByLabel('المدينة').selectOption({ label: 'الرياض' });
    await page.getByLabel('الوصف').fill('سيارة نظيفة وفحص كامل');

    await page.getByRole('button', { name: 'حفظ كمسودة' }).click();
    await expect(page.getByRole('heading', { name: 'الصور' })).toBeVisible();
  });

  await test.step('adds four photos', async () => {
    await page.getByLabel('اختر الصور').setInputFiles(
      [1, 2, 3, 4].map((index) => ({
        name: `car-${index}.png`,
        mimeType: 'image/png',
        buffer: PNG,
      })),
    );
    await page.getByRole('button', { name: 'أضف صورًا' }).click();
    await expect(page.getByTestId('photo-count')).toContainText('4');
  });

  await test.step('and sends it for review, which explains the status', async () => {
    await page.getByRole('button', { name: 'أرسل للمراجعة' }).click();
    await expect(page.getByRole('heading', { name: 'إعلاناتي' })).toBeVisible();
    await expect(page.getByText('قيد المراجعة')).toBeVisible();
    await expect(page.getByTestId('status-reason')).toContainText('بانتظار مراجعة الفريق');
  });

  const listingId = await test.step('an admin approves it', async () => {
    const token = await apiToken(request, ADMIN_PHONE);
    const queue = await request.get(`${API}/listings/moderation/queue`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    const pending = await queue.json();
    const mine = pending.find(
      (listing: { asking_price_sar: number }) => listing.asking_price_sar === 90_000,
    );
    expect(mine, 'the listing should be waiting in the moderation queue').toBeTruthy();

    const approved = await request.post(`${API}/listings/${mine.id}/moderate`, {
      headers: { Authorization: `Bearer ${token}` },
      data: { approve: true },
    });
    expect(approved.ok()).toBeTruthy();
    return mine.id as string;
  });

  await test.step('and a buyer finds it by searching in Arabic', async () => {
    await page.getByRole('button', { name: 'تسجيل الخروج' }).click();
    await page.goto('/');
    await page.getByRole('searchbox').fill('جمس ٢٠١٩');
    await page.getByRole('button', { name: 'ابحث' }).click();

    const results = page.getByTestId('results');
    await expect(results).toBeVisible();
    await expect(results.getByRole('link').first()).toContainText('90,000');
  });

  await test.step('the listing page shows the details but never the floor price', async () => {
    await page.goto(`/listings/${listingId}`);
    await expect(page.getByTestId('listing-price')).toContainText('90,000');
    await expect(page.getByTestId('photos').getByRole('img').first()).toBeVisible();
    await expect(page.getByText('سيارة نظيفة وفحص كامل')).toBeVisible();
    // The seller's private walk-away price must never reach a buyer.
    await expect(page.locator('body')).not.toContainText('82,000');
    await expect(page.locator('body')).not.toContainText('82000');
  });
});

test('a seller marks a car as sold and records the final price', async ({ page, request }) => {
  const sellerPhone = uniquePhone();
  await logIn(page, sellerPhone);

  // Post and approve through the API so this test focuses on the selling step.
  const sellerToken = await apiToken(request, sellerPhone);
  const auth = { Authorization: `Bearer ${sellerToken}` };
  const [cities, makes, models] = await Promise.all([
    request.get(`${API}/cities`).then((r) => r.json()),
    request.get(`${API}/makes`).then((r) => r.json()),
    request.get(`${API}/models`).then((r) => r.json()),
  ]);
  const make = makes.find((m: { slug: string }) => m.slug === 'gmc');
  const model = models.find((m: { make_id: string }) => m.make_id === make.id);

  const created = await request.post(`${API}/listings`, {
    headers: auth,
    data: {
      make_id: make.id,
      model_id: model.id,
      city_id: cities[0].id,
      year: 2020,
      mileage_km: 60000,
      asking_price_sar: 120000,
    },
  });
  const listing = await created.json();

  for (const index of [1, 2, 3, 4]) {
    const upload = await request.post(`${API}/listings/${listing.id}/photos`, {
      headers: auth,
      multipart: {
        file: { name: `p${index}.png`, mimeType: 'image/png', buffer: PNG },
      },
    });
    expect(upload.ok()).toBeTruthy();
  }
  await request.post(`${API}/listings/${listing.id}/publish`, { headers: auth });
  const adminToken = await apiToken(request, ADMIN_PHONE);
  await request.post(`${API}/listings/${listing.id}/moderate`, {
    headers: { Authorization: `Bearer ${adminToken}` },
    data: { approve: true },
  });

  await page.goto('/my-listings');
  await page.getByRole('button', { name: 'تم البيع' }).first().click();
  await page.getByLabel('السعر النهائي بالريال').fill('١١٥٠٠٠');
  await page.getByRole('button', { name: 'تأكيد البيع' }).click();

  await expect(page.getByText('مُباع').first()).toBeVisible();
  await expect(page.getByText(/بيعت بـ\s*115,000/)).toBeVisible();
});
