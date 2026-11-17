import { Component, OnInit, inject, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { Api, errorMessage } from '../core/api.service';
import { AuthService } from '../core/auth.service';
import { AppNotification, Page } from '../core/models';
import { ToastService } from '../core/toast.service';
import { PushService } from '../core/push.service';
import { Pager } from '../shared/pager';

@Component({
  selector: 'app-notifications',
  imports: [DatePipe, Pager],
  template: `
    <div class="page-head">
      <h1>{{ auth.role() === 'admin' ? 'Alerts' : 'Notifications' }}</h1>
      <span class="spacer"></span>
      @if (push.supported() && push.enabled() && !push.subscribed()) {
        <button class="btn sm" type="button" (click)="enablePush()">Enable push notifications</button>
      }
      @if (auth.role() === 'admin') {
        <button class="btn sm" type="button" (click)="runNow()">Run expiry check now</button>
      }
      <button class="btn sm" type="button" (click)="readAll()" [disabled]="!hasUnread()">Mark all read</button>
    </div>
    <div class="card">
      @if (page(); as p) {
        <ul class="list">
          @for (n of p.items; track n.id) {
            <li [style.opacity]="n.read_at ? 0.7 : 1" (click)="markRead(n)">
              <span aria-hidden="true">{{ n.type === 'expired' ? '⛔' : n.type === 'expiry_reminder' ? '⏰' : '🔔' }}</span>
              <div style="flex:1">
                <strong>{{ n.title }}</strong>
                @if (!n.read_at) {
                  <span class="badge blue" style="margin-left:.4rem">New</span>
                }
                <div>{{ n.body }}</div>
                <div class="muted small">{{ n.created_at | date: 'medium' }}</div>
              </div>
            </li>
          } @empty {
            <li class="empty" style="display:block">No notifications yet.</li>
          }
        </ul>
        <app-pager [page]="p.page" [pageSize]="p.page_size" [total]="p.total" (pageChange)="load($event)" />
      }
    </div>
  `,
})
export class NotificationsPage implements OnInit {
  protected auth = inject(AuthService);
  protected push = inject(PushService);
  private api = inject(Api);
  private toast = inject(ToastService);
  protected page = signal<Page<AppNotification> | null>(null);
  protected hasUnread = signal(false);

  ngOnInit() {
    this.load(1);
    this.push.init();
  }

  load(page: number) {
    this.api.get<Page<AppNotification>>('/notifications', { page, page_size: 20 }).subscribe((p) => {
      this.page.set(p);
      this.hasUnread.set(p.items.some((n) => !n.read_at));
    });
  }

  markRead(n: AppNotification) {
    if (n.read_at) return;
    this.api.post(`/notifications/${n.id}/read`).subscribe(() => this.load(this.page()?.page ?? 1));
  }

  readAll() {
    this.api.post('/notifications/read-all').subscribe(() => this.load(1));
  }

  runNow() {
    this.api.post<{ created: number }>('/notifications/run-reminders').subscribe({
      next: (r) => {
        this.toast.ok(`${r.created} new notification(s) generated`);
        this.load(1);
      },
      error: (e) => this.toast.error(errorMessage(e)),
    });
  }

  async enablePush() {
    try {
      await this.push.subscribe();
      this.toast.ok('Push notifications enabled on this device');
    } catch (e: any) {
      this.toast.error(e?.message ?? 'Could not enable push notifications');
    }
  }
}
