import { Component, OnInit, inject, signal } from '@angular/core';
import { FormBuilder, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { Api, errorMessage } from '../../core/api.service';
import { AuthService } from '../../core/auth.service';
import { Policy } from '../../core/models';
import { ToastService } from '../../core/toast.service';
import { SHARED } from '../../shared';

interface Kiosk {
  id: number;
  name: string;
  created_at: string;
  last_seen_at: string | null;
  revoked_at: string | null;
}

interface AdminAccount {
  id: number;
  username: string;
  email: string | null;
  is_active: boolean;
  must_change_password: boolean;
  created_at: string;
}

@Component({
  selector: 'app-settings',
  imports: [ReactiveFormsModule, FormsModule, ...SHARED],
  template: `
    <div class="page-head"><h1>Settings</h1></div>
    <div class="grid two">
      <section class="card">
        <h2>Gym rules in effect</h2>
        @if (policy(); as p) {
          <dl class="kv">
            <dt>Time zone</dt>
            <dd>{{ p.timezone }}</dd>
            <dt>Gym day starts</dt>
            <dd>{{ hour(p.gym_day_start_hour) }}</dd>
            <dt>Check-ins per day</dt>
            <dd>{{ p.attendance_max_checkins_per_day === 0 ? 'Unlimited' : p.attendance_max_checkins_per_day }}</dd>
            <dt>Check-in without active plan</dt>
            <dd>{{ p.attendance_require_active_subscription ? 'Blocked' : 'Allowed' }}</dd>
            <dt>QR code rotates every</dt>
            <dd>{{ p.qr_token_ttl_seconds }} seconds</dd>
            <dt>Expiry reminders</dt>
            <dd>{{ reminderText(p.reminder_days_before_expiry) }}</dd>
            <dt>Members can edit</dt>
            <dd>{{ fieldsText(p.member_editable_fields) }}</dd>
          </dl>
          <p class="muted small" style="margin-bottom:0">
            These are set in the server configuration (see the README) so they can't be changed by accident. Ask your developer to change
            them.
          </p>
        }
      </section>

      <section class="card">
        <div class="page-head" style="margin-bottom:.5rem">
          <h2 style="margin:0">Admin accounts</h2>
          <span class="spacer"></span>
          <button class="btn sm primary" type="button" (click)="openCreate()">+ Add admin</button>
        </div>
        <ul class="list">
          @for (a of admins(); track a.id) {
            <li>
              <div style="flex:1">
                <strong>{{ a.username }}</strong>
                @if (a.id === auth.user()?.id) {
                  <span class="muted small">(you)</span>
                }
                <div class="muted small">{{ a.email || 'No email' }} · added {{ a.created_at | date: 'd MMM y' }}</div>
              </div>
              <app-badge [value]="a.is_active ? 'active' : 'inactive'" />
              @if (a.id !== auth.user()?.id) {
                <button class="btn sm" type="button" (click)="toggle(a)">{{ a.is_active ? 'Deactivate' : 'Activate' }}</button>
                <button class="btn sm" type="button" (click)="resetFor.set(a)">Reset password</button>
              }
            </li>
          }
        </ul>
      </section>
    </div>

    <section class="card" style="margin-top:1rem">
      <div class="page-head" style="margin-bottom:.5rem">
        <div>
          <h2 style="margin:0">QR display screens</h2>
          <div class="muted small">Links for the tablet or TV at the entrance. They can only show the check-in QR code.</div>
        </div>
        <span class="spacer"></span>
        <button class="btn sm primary" type="button" (click)="kioskOpen.set(true)">+ New display link</button>
      </div>
      @if (newKioskUrl(); as url) {
        <div class="alert ok">
          <strong>Open this link on the display device.</strong> It is shown only once.
          <div class="actions" style="margin-top:.5rem;align-items:center">
            <code style="overflow-wrap:anywhere;flex:1">{{ url }}</code>
            <button class="btn sm" type="button" (click)="copy(url)">Copy</button>
          </div>
        </div>
      }
      <ul class="list">
        @for (k of kiosks(); track k.id) {
          <li>
            <div style="flex:1">
              <strong>{{ k.name }}</strong>
              <div class="muted small">
                Created {{ k.created_at | date: 'd MMM y' }} ·
                {{ k.last_seen_at ? 'last active ' + (k.last_seen_at | date: 'd MMM, h:mm a') : 'never used' }}
              </div>
            </div>
            @if (k.revoked_at) {
              <app-badge value="cancelled" text="Revoked" />
            } @else {
              <app-badge value="active" />
              <button class="btn sm danger" type="button" (click)="revoke(k)">Revoke</button>
            }
          </li>
        } @empty {
          <li class="muted">No display links yet. Until you create one, the QR screen needs an admin login.</li>
        }
      </ul>
    </section>

    <app-modal title="New display link" [open]="kioskOpen()" (closed)="kioskOpen.set(false)">
      <form class="form" (ngSubmit)="createKiosk()">
        <div class="field">
          <label for="kn">Name</label>
          <input id="kn" name="kn" [(ngModel)]="kioskName" placeholder="e.g. Front door tablet" required maxlength="100" />
        </div>
        <div class="actions"><button class="btn primary" type="submit" [disabled]="!kioskName.trim()">Create link</button></div>
      </form>
    </app-modal>

    <app-modal title="Add admin" [open]="createOpen()" (closed)="createOpen.set(false)">
      @if (error()) {
        <div class="alert error" role="alert">{{ error() }}</div>
      }
      <form class="form" [formGroup]="form" (ngSubmit)="create()">
        <div class="field">
          <label for="au">Username *</label>
          <input id="au" formControlName="username" autocomplete="off" autocapitalize="off" />
          <span class="hint">Letters, numbers and . _ - &#64; only.</span>
        </div>
        <div class="field"><label for="ae2">Email</label><input id="ae2" type="email" formControlName="email" /></div>
        <div class="field">
          <label for="ap">Temporary password *</label>
          <input id="ap" formControlName="password" autocomplete="new-password" />
          <span class="hint">They'll be asked to change it at first sign-in.</span>
        </div>
        <div class="actions"><button class="btn primary" type="submit" [disabled]="form.invalid">Create admin</button></div>
      </form>
    </app-modal>

    <app-modal title="Reset admin password" [open]="!!resetFor()" (closed)="resetFor.set(null)">
      <form class="form" (ngSubmit)="reset()">
        <div class="field">
          <label for="arp">New temporary password for {{ resetFor()?.username }}</label>
          <input id="arp" name="arp" [(ngModel)]="newPassword" minlength="8" required />
        </div>
        <div class="actions"><button class="btn primary" type="submit" [disabled]="newPassword.length < 8">Reset password</button></div>
      </form>
    </app-modal>
  `,
})
export class SettingsPage implements OnInit {
  protected auth = inject(AuthService);
  private api = inject(Api);
  private toast = inject(ToastService);
  protected policy = signal<Policy | null>(null);
  protected admins = signal<AdminAccount[]>([]);
  protected createOpen = signal(false);
  protected resetFor = signal<AdminAccount | null>(null);
  protected error = signal('');
  newPassword = '';
  kioskName = '';
  protected kiosks = signal<Kiosk[]>([]);
  protected kioskOpen = signal(false);
  protected newKioskUrl = signal<string | null>(null);
  protected form = inject(FormBuilder).nonNullable.group({
    username: ['', [Validators.required, Validators.minLength(3), Validators.pattern(/^[A-Za-z0-9_.@-]+$/)]],
    email: ['', Validators.email],
    password: ['', [Validators.required, Validators.minLength(8)]],
  });

  ngOnInit() {
    this.api.get<Policy>('/settings/policy').subscribe((p) => this.policy.set(p));
    this.loadAdmins();
    this.loadKiosks();
  }

  loadKiosks() {
    this.api.get<Kiosk[]>('/kiosks').subscribe((k) => this.kiosks.set(k));
  }

  createKiosk() {
    this.api.post<Kiosk & { token: string }>('/kiosks', { name: this.kioskName.trim() }).subscribe({
      next: (k) => {
        this.kioskOpen.set(false);
        this.kioskName = '';
        this.newKioskUrl.set(`${location.origin}/kiosk#${k.token}`);
        this.loadKiosks();
      },
      error: (e) => this.toast.error(errorMessage(e)),
    });
  }

  revoke(k: Kiosk) {
    if (!confirm(`Revoke "${k.name}"? That screen will stop showing the QR code.`)) return;
    this.api.delete(`/kiosks/${k.id}`).subscribe(() => this.loadKiosks());
  }

  copy(text: string) {
    navigator.clipboard?.writeText(text).then(
      () => this.toast.ok('Link copied'),
      () => this.toast.error('Copy failed; select the link and copy it manually'),
    );
  }

  loadAdmins() {
    this.api.get<AdminAccount[]>('/admins').subscribe((a) => this.admins.set(a));
  }

  hour(h: number) {
    return h === 0 ? 'Midnight' : new Date(2000, 0, 1, h).toLocaleTimeString('en-IN', { hour: 'numeric', minute: '2-digit' });
  }

  reminderText(days: number[]) {
    if (!days.length) return 'Off';
    return days.map((d) => (d === 0 ? 'on the expiry day' : `${d} day${d === 1 ? '' : 's'} before`)).join(', ') + ', plus an expiry notice';
  }

  fieldsText(f: string[]) {
    return f.length ? f.map((x) => x.replace(/_/g, ' ').replace('photo url', 'photo')).join(', ') : 'Nothing';
  }

  openCreate() {
    this.error.set('');
    this.form.reset({ username: '', email: '', password: '' });
    this.createOpen.set(true);
  }

  create() {
    const v = this.form.getRawValue();
    this.api.post('/admins', { ...v, email: v.email || null }).subscribe({
      next: () => {
        this.createOpen.set(false);
        this.toast.show(`Admin ${v.username} created. Temporary password: ${v.password}`, 'ok', 20000);
        this.loadAdmins();
      },
      error: (e) => this.error.set(errorMessage(e)),
    });
  }

  toggle(a: AdminAccount) {
    if (a.is_active && !confirm(`Deactivate ${a.username}? They will be signed out.`)) return;
    this.api.post(`/admins/${a.id}/status`, { is_active: !a.is_active }).subscribe({
      next: () => this.loadAdmins(),
      error: (e) => this.toast.error(errorMessage(e)),
    });
  }

  reset() {
    const a = this.resetFor();
    if (!a) return;
    this.api.post(`/admins/${a.id}/reset-password`, { new_password: this.newPassword }).subscribe({
      next: () => {
        this.toast.show(`Password reset for ${a.username}: ${this.newPassword}`, 'ok', 20000);
        this.resetFor.set(null);
        this.newPassword = '';
      },
      error: (e) => this.toast.error(errorMessage(e)),
    });
  }
}
