import { defineConfig, devices } from '@playwright/test';

/**
 * End-to-end flows against a running stack:
 *   backend:  uvicorn app.main:app --port 8000   (seeded with `python -m app.cli seed-demo`)
 *   frontend: npm start                          (http://localhost:4200, proxies /api)
 * Run: npm run e2e
 */
export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: process.env['CI'] ? [['list'], ['html', { open: 'never' }]] : 'list',
  use: {
    baseURL: process.env['E2E_BASE_URL'] ?? 'http://localhost:4200',
    trace: 'off',
    screenshot: 'only-on-failure',
    launchOptions: process.env['PW_CHROMIUM_PATH'] ? { executablePath: process.env['PW_CHROMIUM_PATH'] } : {},
  },
  projects: [
    { name: 'desktop', use: { ...devices['Desktop Chrome'] } },
    {
      name: 'phone',
      use: {
        ...devices['Pixel 7'],
        launchOptions: {
          ...(process.env['PW_CHROMIUM_PATH'] ? { executablePath: process.env['PW_CHROMIUM_PATH'] } : {}),
          // A fake camera that shows the gym QR code (written by the test).
          args: ['--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream', '--use-file-for-fake-video-capture=e2e/.qr.y4m'],
        },
      },
    },
  ],
});
