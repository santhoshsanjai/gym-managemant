import { expect, test } from '@playwright/test';
import { ADMIN, login, uniqueMobile } from './helpers';

test.describe('admin', () => {
  test.skip(({ isMobile }) => isMobile, 'admin flows run on desktop');

  test('register a member, assign a package with payment, and see it on the dashboard', async ({ page }) => {
    await login(page, ADMIN.username, ADMIN.password);
    await expect(page.getByText('Total members')).toBeVisible();

    await page.getByRole('link', { name: '+ New member' }).click();
    const mobile = uniqueMobile();
    await page.fill('#name', 'E2E Member');
    await page.fill('#mobile', mobile);
    await page.getByRole('button', { name: 'Register member' }).click();
    await expect(page.getByRole('heading', { name: 'E2E Member' })).toBeVisible();

    await page.getByRole('button', { name: 'Assign package' }).first().click();
    await page.selectOption('#pkg', { index: 1 });
    await page.selectOption('#method', 'upi');
    await page.locator('app-subscription-form button[type=submit]').click();
    await expect(page.getByText('Subscription saved')).toBeVisible();
    await expect(page.getByText('Membership active')).toBeVisible();

    await page.getByRole('tab', { name: 'Payments' }).click();
    await expect(page.locator('td', { hasText: 'Upi' })).toBeVisible();

    await page.getByRole('link', { name: 'Members' }).first().click();
    await page.getByLabel('Search members').fill(mobile);
    await expect(page.locator('tbody tr')).toHaveCount(1);
  });

  test('payments month view and report download', async ({ page }) => {
    await login(page, ADMIN.username, ADMIN.password);
    await page.goto('/admin/reports');
    const [download] = await Promise.all([
      page.waitForEvent('download'),
      page.getByRole('button', { name: 'Download .xlsx' }).first().click(),
    ]);
    expect(download.suggestedFilename()).toMatch(/^payments-\d{4}-\d{2}\.xlsx$/);
  });

  test('kiosk link shows the QR without an admin session', async ({ page, browser }) => {
    await login(page, ADMIN.username, ADMIN.password);
    await page.goto('/admin/settings');
    await page.getByRole('button', { name: '+ New display link' }).click();
    await page.fill('#kn', 'E2E screen');
    await page.getByRole('button', { name: 'Create link' }).click();
    const url = (await page.locator('.alert.ok code').textContent())!.trim();

    const kioskCtx = await browser.newContext();
    const kiosk = await kioskCtx.newPage();
    await kiosk.goto(url);
    await expect(kiosk.locator('.qr-box img')).toBeVisible();
    await expect(kiosk).toHaveURL(/\/kiosk$/); // secret removed from the address bar
    await kiosk.goto('/admin');
    await expect(kiosk).toHaveURL(/\/login/); // no admin access from the kiosk
    await kioskCtx.close();
  });

  test('members cannot open admin pages', async ({ page }) => {
    await page.goto('/admin/members');
    await expect(page).toHaveURL(/\/login/);
  });
});
