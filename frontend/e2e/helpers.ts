import { APIRequestContext, Page, expect } from '@playwright/test';

export const ADMIN = { username: 'admin', password: 'admin12345' };

export async function submitLogin(page: Page, username: string, password: string) {
  await page.goto('/login');
  await page.fill('#username', username);
  await page.fill('#password', password);
  await page.click('button[type=submit]');
}

/** Signs in and waits until the app has left the login page. */
export async function login(page: Page, username: string, password: string) {
  await submitLogin(page, username, password);
  await page.waitForURL((u) => !u.pathname.startsWith('/login'));
}

export async function apiToken(request: APIRequestContext, username: string, password: string) {
  const r = await request.post('/api/auth/login', { data: { username, password } });
  expect(r.ok()).toBeTruthy();
  return (await r.json()).access_token as string;
}

/** Unique 10-digit mobile number per test run. */
export function uniqueMobile() {
  return '7' + String(Date.now()).slice(-9);
}
