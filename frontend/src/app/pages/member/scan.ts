import { Component, ElementRef, OnDestroy, OnInit, inject, signal, viewChild } from '@angular/core';
import { DatePipe } from '@angular/common';
import { RouterLink } from '@angular/router';
import { BrowserQRCodeReader, IScannerControls } from '@zxing/browser';
import { Api, errorMessage } from '../../core/api.service';
import { Attendance } from '../../core/models';

type State = 'starting' | 'scanning' | 'submitting' | 'success' | 'error';

@Component({
  selector: 'app-scan',
  imports: [RouterLink, DatePipe],
  template: `
    <div class="page-head"><h1>Check in</h1></div>
    <div class="card" style="max-width:520px;margin:0 auto;text-align:center">
      @switch (state()) {
        @case ('success') {
          <div style="font-size:3rem" aria-hidden="true">✅</div>
          <h2>{{ message() }}</h2>
          <p class="muted">{{ result()?.checked_in_at | date: 'EEEE, d MMM · h:mm a' }}</p>
          <a class="btn primary block" routerLink="/member">Done</a>
        }
        @case ('error') {
          <div style="font-size:3rem" aria-hidden="true">⚠️</div>
          <h2 role="alert">{{ message() }}</h2>
          <div class="actions" style="justify-content:center">
            <button class="btn primary" type="button" (click)="start()">Try again</button>
            <a class="btn" routerLink="/member">Back</a>
          </div>
        }
        @default {
          <p class="muted">Point your camera at the QR code displayed at the gym entrance.</p>
          <div class="scanner">
            <video #video playsinline muted aria-label="Camera preview"></video>
            <div class="frame" aria-hidden="true"></div>
          </div>
          <p class="muted small">
            {{ state() === 'submitting' ? 'Checking in…' : state() === 'starting' ? 'Starting camera…' : 'Scanning…' }}
          </p>
        }
      }
    </div>
  `,
  styles: `
    .scanner {
      position: relative;
      width: 100%;
      aspect-ratio: 1;
      background: #000;
      border-radius: 12px;
      overflow: hidden;
    }
    video {
      width: 100%;
      height: 100%;
      object-fit: cover;
    }
    .frame {
      position: absolute;
      inset: 15%;
      border: 3px solid rgb(255 255 255 / 0.85);
      border-radius: 16px;
      box-shadow: 0 0 0 999px rgb(0 0 0 / 0.35);
    }
  `,
})
export class ScanPage implements OnInit, OnDestroy {
  private api = inject(Api);
  private video = viewChild<ElementRef<HTMLVideoElement>>('video');
  protected state = signal<State>('starting');
  protected message = signal('');
  protected result = signal<Attendance | null>(null);
  private controls?: IScannerControls;
  private reader = new BrowserQRCodeReader(undefined, { delayBetweenScanAttempts: 250 });

  ngOnInit() {
    this.start();
  }

  ngOnDestroy() {
    this.stop();
  }

  async start() {
    this.state.set('starting');
    this.message.set('');
    if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) {
      return this.fail('Camera access needs a secure (HTTPS) connection and a supported browser.');
    }
    // Wait for the <video> element to render.
    await new Promise((r) => setTimeout(r));
    const el = this.video()?.nativeElement;
    if (!el) return this.fail('Camera preview unavailable.');
    try {
      this.controls = await this.reader.decodeFromConstraints(
        { video: { facingMode: { ideal: 'environment' } }, audio: false },
        el,
        (res) => {
          if (res && this.state() === 'scanning') this.submit(res.getText());
        },
      );
      this.state.set('scanning');
    } catch (e: any) {
      const denied = e?.name === 'NotAllowedError' || e?.name === 'SecurityError';
      this.fail(
        denied
          ? 'Camera permission was denied. Allow camera access in your browser settings and try again.'
          : 'Could not start the camera.',
      );
    }
  }

  private submit(payload: string) {
    this.state.set('submitting');
    this.stop();
    this.api.post<{ message: string; attendance: Attendance }>('/attendance/check-in', { qr_payload: payload }).subscribe({
      next: (r) => {
        this.message.set(r.message);
        this.result.set(r.attendance);
        this.state.set('success');
        navigator.vibrate?.(80);
      },
      error: (e) => this.fail(errorMessage(e)),
    });
  }

  private fail(msg: string) {
    this.stop();
    this.message.set(msg);
    this.state.set('error');
  }

  private stop() {
    this.controls?.stop();
    this.controls = undefined;
  }
}
