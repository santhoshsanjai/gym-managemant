import { Injectable, inject, signal } from '@angular/core';
import { SwPush } from '@angular/service-worker';
import { firstValueFrom } from 'rxjs';
import { Api } from './api.service';

/** Optional Web Push. Works only when the server has VAPID keys configured,
 * the app is served over HTTPS with the service worker active, and the user
 * grants notification permission. In-app notifications work regardless. */
@Injectable({ providedIn: 'root' })
export class PushService {
  private swPush = inject(SwPush);
  private api = inject(Api);
  readonly supported = signal(this.swPush.isEnabled);
  readonly enabled = signal(false);
  readonly subscribed = signal(false);
  private key: string | null = null;
  private initialised = false;

  init() {
    if (this.initialised || !this.swPush.isEnabled) return;
    this.initialised = true;
    this.api.get<{ public_key: string | null; enabled: boolean }>('/notifications/push/public-key').subscribe((r) => {
      this.key = r.public_key;
      this.enabled.set(r.enabled);
    });
    this.swPush.subscription.subscribe((s) => this.subscribed.set(!!s));
  }

  async subscribe() {
    if (!this.key) throw new Error('Push notifications are not configured on the server');
    const sub = await this.swPush.requestSubscription({ serverPublicKey: this.key });
    await firstValueFrom(this.api.post('/notifications/push/subscribe', sub.toJSON()));
    this.subscribed.set(true);
  }
}
