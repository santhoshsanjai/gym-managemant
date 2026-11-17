import { Component, OnDestroy, OnInit, inject, signal } from '@angular/core';
import QRCode from 'qrcode';
import { Api, errorMessage } from '../../core/api.service';

interface QrToken {
  qr_payload: string;
  expires_at: string;
  ttl_seconds: number;
  server_time: string;
}

/** Full-screen kiosk page for a tablet/monitor at the gym entrance. The QR
 * token rotates on the server; this page polls shortly before expiry. */
@Component({
  selector: 'app-qr-display',
  template: `
    <div class="qr-page">
      <h1>Scan to check in</h1>
      <p>Open the Gym app on your phone and tap <strong>Check in</strong>.</p>
      <div class="qr-box">
        @if (img()) {
          <img [src]="img()" alt="Gym check-in QR code" width="360" height="360" />
        } @else {
          <div class="qr-placeholder">Loading…</div>
        }
      </div>
      @if (error()) {
        <p class="qr-error">{{ error() }}</p>
      } @else {
        <p class="qr-timer">Code refreshes in {{ secondsLeft() }}s</p>
      }
      <p class="qr-clock">{{ clock() }}</p>
    </div>
  `,
  styles: `
    .qr-page {
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      text-align: center;
      padding: 1rem;
      background: #111827;
      color: #fff;
    }
    h1 {
      font-size: clamp(1.8rem, 5vw, 3rem);
      margin-bottom: 0.25rem;
    }
    p {
      color: #d1d5db;
      font-size: 1.1rem;
    }
    .qr-box {
      background: #fff;
      padding: 1.25rem;
      border-radius: 20px;
      margin: 1rem 0;
    }
    img {
      width: min(70vmin, 420px);
      height: auto;
      display: block;
    }
    .qr-placeholder {
      width: min(70vmin, 420px);
      aspect-ratio: 1;
      display: grid;
      place-items: center;
      color: #111827;
    }
    .qr-timer {
      font-variant-numeric: tabular-nums;
    }
    .qr-error {
      color: #fca5a5;
    }
    .qr-clock {
      font-size: 1.5rem;
      font-variant-numeric: tabular-nums;
      color: #9ca3af;
    }
  `,
})
export class QrDisplayPage implements OnInit, OnDestroy {
  private api = inject(Api);
  protected img = signal<string | null>(null);
  protected error = signal('');
  protected secondsLeft = signal(0);
  protected clock = signal('');
  private payload = '';
  private expiresAt = 0;
  private skew = 0; // server minus local clock, ms
  private tick?: ReturnType<typeof setInterval>;
  private wakeLock: any;

  ngOnInit() {
    this.fetch();
    this.tick = setInterval(() => this.onTick(), 1000);
    (navigator as any).wakeLock
      ?.request('screen')
      .then((l: any) => (this.wakeLock = l))
      .catch(() => {});
  }

  ngOnDestroy() {
    clearInterval(this.tick);
    this.wakeLock?.release?.();
  }

  private onTick() {
    const now = Date.now() + this.skew;
    this.clock.set(new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' }));
    const left = Math.max(0, Math.round((this.expiresAt - now) / 1000));
    this.secondsLeft.set(left);
    if (left <= 4) this.fetch();
  }

  private fetching = false;
  private fetch() {
    if (this.fetching) return;
    this.fetching = true;
    this.api.get<QrToken>('/attendance/qr/current').subscribe({
      next: async (t) => {
        this.fetching = false;
        this.error.set('');
        this.skew = new Date(t.server_time).getTime() - Date.now();
        this.expiresAt = new Date(t.expires_at).getTime();
        if (t.qr_payload !== this.payload) {
          this.payload = t.qr_payload;
          this.img.set(await QRCode.toDataURL(t.qr_payload, { width: 720, margin: 1, errorCorrectionLevel: 'M' }));
        }
      },
      error: (e) => {
        this.fetching = false;
        this.error.set(`Can't refresh the code: ${errorMessage(e)}. Retrying…`);
      },
    });
  }
}
