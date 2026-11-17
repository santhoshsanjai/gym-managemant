import { execFileSync } from 'node:child_process';
import { writeFileSync } from 'node:fs';
import { expect, test } from '@playwright/test';
import QRCode from 'qrcode';
import { ADMIN, apiToken, login, submitLogin, uniqueMobile } from './helpers';

/** Creates a member with an active subscription through the API. */
async function setupMember(request: import('@playwright/test').APIRequestContext) {
  const token = await apiToken(request, ADMIN.username, ADMIN.password);
  const headers = { Authorization: `Bearer ${token}` };
  const mobile = uniqueMobile();
  const m = await (await request.post('/api/members', { headers, data: { full_name: 'Scan Tester', mobile, password: 'first-pass-1' } })).json();
  const pkgs = await (await request.get('/api/packages', { headers })).json();
  const sub = await request.post('/api/subscriptions', { headers, data: { member_id: m.id, package_id: pkgs[0].id } });
  expect(sub.ok()).toBeTruthy();
  const qr = await (await request.get('/api/attendance/qr/current', { headers })).json();
  return { mobile, qrPayload: qr.qr_payload as string };
}

test.describe('member', () => {
  test.skip(({ isMobile }) => !isMobile, 'member flows run on a phone');

  test('first sign-in, camera check-in, duplicate blocked, history', async ({ page, request }) => {
    const { mobile, qrPayload } = await setupMember(request);
    // Feed the current gym QR code to the fake camera.
    const png = 'e2e/.qr.png';
    await QRCode.toFile(png, qrPayload, { width: 480, margin: 4 });
    execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-loop', '1', '-i', png, '-vf', 'scale=480:480,pad=640:480:80:0:color=white', '-t', '2', '-pix_fmt', 'yuv420p', 'e2e/.qr.y4m']);

    await login(page, mobile, 'first-pass-1');
    await expect(page).toHaveURL(/change-password/);
    await page.fill('#cur', 'first-pass-1');
    await page.fill('#new', 'second-pass-2');
    await page.fill('#confirm', 'second-pass-2');
    await page.click('button[type=submit]');
    await expect(page.getByText('Ready for your workout?')).toBeVisible();

    await page.getByRole('link', { name: 'Scan gym QR to check in' }).click();
    await expect(page.getByText(/Attendance recorded/)).toBeVisible({ timeout: 20_000 });

    await page.goto('/member/scan');
    await expect(page.getByText('You have already checked in today.')).toBeVisible({ timeout: 20_000 });

    await page.goto('/member/attendance');
    await expect(page.locator('.stat.accent .value')).toHaveText('1');
    await page.goto('/member');
    await expect(page.getByText('Checked in today')).toBeVisible();
  });

  test('wrong password shows an error', async ({ page }) => {
    await submitLogin(page, 'nobody', 'wrong-password');
    await expect(page.getByRole('alert')).toContainText('Incorrect username or password');
  });
});
