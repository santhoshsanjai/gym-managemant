import { Component, OnInit, inject, input, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { Api, errorMessage } from '../../core/api.service';
import { Attendance, Member, Page, Payment, Subscription } from '../../core/models';
import { ToastService } from '../../core/toast.service';
import { SHARED } from '../../shared';
import { PaymentForm } from '../../shared/payment-form';
import { PhotoUpload } from '../../shared/photo-upload';
import { SubscriptionForm } from '../../shared/subscription-form';

type Tab = 'subscriptions' | 'payments' | 'attendance';

@Component({
  selector: 'app-member-detail',
  imports: [RouterLink, FormsModule, SubscriptionForm, PaymentForm, PhotoUpload, ...SHARED],
  template: `
    @if (m(); as m) {
      <div class="page-head">
        <a class="btn ghost sm" routerLink="/admin/members">← Members</a>
        <app-avatar [name]="m.full_name" [src]="m.photo_url" [size]="48" />
        <div>
          <h1>{{ m.full_name }}</h1>
          <div class="sub">{{ m.member_code }} · joined {{ m.joining_date | date: 'd MMM y' }}</div>
        </div>
        <app-badge
          [value]="m.membership_state"
          [text]="m.membership_state === 'none' ? 'No membership' : 'Membership ' + m.membership_state"
        />
        <app-badge [value]="m.status" [text]="'Account ' + m.status" />
        <span class="spacer"></span>
        <div class="actions">
          <a class="btn" [routerLink]="['/admin/members', m.id, 'edit']">Edit</a>
          <button class="btn" type="button" (click)="toggleStatus()">{{ m.status === 'active' ? 'Deactivate' : 'Activate' }}</button>
          <button class="btn" type="button" (click)="resetOpen.set(true)">Reset password</button>
        </div>
      </div>

      <div class="grid two">
        <section class="card">
          <h2>Profile</h2>
          <app-photo-upload
            [name]="m.full_name"
            [url]="m.photo_url"
            [uploadPath]="'/members/' + m.id + '/photo'"
            [removePath]="'/members/' + m.id + '/photo'"
            (changed)="onPhoto($event)"
          />
          <div style="height:1rem"></div>
          <dl class="kv">
            <dt>Mobile</dt>
            <dd>{{ m.mobile }}</dd>
            <dt>Email</dt>
            <dd>{{ m.email || '—' }}</dd>
            <dt>Gender</dt>
            <dd>{{ m.gender | humanize }}</dd>
            <dt>Date of birth</dt>
            <dd>{{ m.date_of_birth ? (m.date_of_birth | date: 'd MMM y') : '—' }}</dd>
            <dt>Trainer</dt>
            <dd>{{ m.trainer?.full_name || '—' }}</dd>
            <dt>Address</dt>
            <dd>{{ m.address || '—' }}</dd>
          </dl>
        </section>
        <section class="card">
          <h2>Membership</h2>
          @if (current(); as s) {
            <dl class="kv">
              <dt>Package</dt>
              <dd>{{ s.package_name }} ({{ s | duration }})</dd>
              <dt>Period</dt>
              <dd>{{ s.start_date | date: 'd MMM y' }} – {{ s.expiry_date | date: 'd MMM y' }}</dd>
              <dt>Status</dt>
              <dd>
                <app-badge [value]="s.state" />
                @if (s.state === 'active') {
                  <span class="muted small">{{ s.remaining_days }} days left</span>
                }
              </dd>
              <dt>Paid</dt>
              <dd>{{ s.amount_paid | currency: 'INR' : 'symbol' : '1.0-2' }} of {{ s.amount | currency: 'INR' : 'symbol' : '1.0-2' }}</dd>
            </dl>
          } @else {
            <p class="muted">No subscription yet.</p>
          }
          <div class="actions" style="margin-top:1rem">
            @if (current(); as s) {
              <button class="btn primary" type="button" (click)="openRenew(s)" [disabled]="m.status !== 'active'">Renew</button>
            } @else {
              <button class="btn primary" type="button" (click)="openAssign()" [disabled]="m.status !== 'active'">Assign package</button>
            }
            <button class="btn" type="button" (click)="payFor.set(current()); payOpen.set(true)">Record payment</button>
            <button class="btn" type="button" (click)="manualCheckIn()">Mark attendance today</button>
          </div>
        </section>
      </div>

      <div class="card" style="margin-top:1rem">
        <div class="actions" role="tablist" style="margin-bottom:1rem">
          @for (t of tabs; track t) {
            <button
              class="btn sm"
              role="tab"
              [class.primary]="tab() === t"
              [attr.aria-selected]="tab() === t"
              type="button"
              (click)="tab.set(t)"
            >
              {{ t | humanize }}
            </button>
          }
          <span class="spacer"></span>
          @if (tab() === 'subscriptions') {
            <button class="btn sm" type="button" (click)="openAssign()">+ New subscription</button>
          }
        </div>
        @switch (tab()) {
          @case ('subscriptions') {
            <div class="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Package</th>
                    <th>Start</th>
                    <th>Expiry</th>
                    <th>Amount</th>
                    <th>Paid</th>
                    <th>Status</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  @for (s of subs(); track s.id) {
                    <tr>
                      <td>
                        {{ s.package_name }}
                        @if (s.renewed_from_id) {
                          <span class="muted small">(renewal)</span>
                        }
                      </td>
                      <td>{{ s.start_date | date: 'd MMM y' }}</td>
                      <td>{{ s.expiry_date | date: 'd MMM y' }}</td>
                      <td>{{ s.amount | currency: 'INR' : 'symbol' : '1.0-2' }}</td>
                      <td>{{ s.amount_paid | currency: 'INR' : 'symbol' : '1.0-2' }}</td>
                      <td><app-badge [value]="s.state" /></td>
                      <td class="right">
                        <select
                          class="btn sm"
                          style="width:auto"
                          (change)="subAction(s, $any($event.target))"
                          aria-label="Subscription actions"
                        >
                          <option value="">Actions…</option>
                          <option value="renew">Renew</option>
                          <option value="pay">Record payment</option>
                          @if (s.status !== 'active') {
                            <option value="active">Reactivate</option>
                          }
                          @if (s.status === 'active') {
                            <option value="suspended">Suspend</option>
                          }
                          @if (s.status !== 'cancelled') {
                            <option value="cancelled">Cancel</option>
                          }
                        </select>
                      </td>
                    </tr>
                  } @empty {
                    <tr>
                      <td colspan="7" class="empty">No subscriptions.</td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>
          }
          @case ('payments') {
            <div class="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Amount</th>
                    <th>Method</th>
                    <th>Package</th>
                    <th>Reference</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  @for (p of payments()?.items; track p.id) {
                    <tr>
                      <td>{{ p.payment_date | date: 'd MMM y' }}</td>
                      <td class="mono">{{ p.amount | currency: 'INR' : 'symbol' : '1.0-2' }}</td>
                      <td>{{ p.method | humanize }}</td>
                      <td>{{ p.package_name || '—' }}</td>
                      <td>{{ p.reference || '—' }}</td>
                      <td><app-badge [value]="p.status" /></td>
                    </tr>
                  } @empty {
                    <tr>
                      <td colspan="6" class="empty">No payments recorded.</td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>
            @if (payments(); as p) {
              <app-pager [page]="p.page" [pageSize]="p.page_size" [total]="p.total" (pageChange)="loadPayments($event)" />
            }
          }
          @case ('attendance') {
            <div class="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Time</th>
                    <th>Source</th>
                  </tr>
                </thead>
                <tbody>
                  @for (a of attendance()?.items; track a.id) {
                    <tr>
                      <td>{{ a.attendance_date | date: 'EEE, d MMM y' }}</td>
                      <td>{{ a.checked_in_at | date: 'h:mm a' }}</td>
                      <td><app-badge [value]="a.source" [text]="a.source === 'qr' ? 'QR scan' : 'Manual'" /></td>
                    </tr>
                  } @empty {
                    <tr>
                      <td colspan="3" class="empty">No attendance yet.</td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>
            @if (attendance(); as p) {
              <app-pager [page]="p.page" [pageSize]="p.page_size" [total]="p.total" (pageChange)="loadAttendance($event)" />
            }
          }
        }
      </div>

      <app-modal [title]="renewFrom() ? 'Renew subscription' : 'Assign package'" [open]="subOpen()" (closed)="subOpen.set(false)">
        @if (subOpen()) {
          <app-subscription-form
            [memberId]="m.id"
            [renewFrom]="renewFrom()"
            (saved)="afterSave('Subscription saved')"
            (cancelled)="subOpen.set(false)"
          />
        }
      </app-modal>
      <app-modal title="Record payment" [open]="payOpen()" (closed)="payOpen.set(false)">
        @if (payOpen()) {
          <app-payment-form
            [memberId]="m.id"
            [subscription]="payFor()"
            (saved)="afterSave('Payment recorded')"
            (cancelled)="payOpen.set(false)"
          />
        }
      </app-modal>
      <app-modal title="Reset password" [open]="resetOpen()" (closed)="resetOpen.set(false)">
        <form class="form" (ngSubmit)="resetPassword()">
          <div class="field">
            <label for="npw">New temporary password</label>
            <input id="npw" name="npw" [(ngModel)]="newPassword" minlength="8" required />
            <span class="hint">The member will be asked to change it after signing in.</span>
          </div>
          <div class="actions"><button class="btn primary" type="submit" [disabled]="newPassword.length < 8">Reset password</button></div>
        </form>
      </app-modal>
    } @else {
      <p class="muted">Loading…</p>
    }
  `,
})
export class MemberDetailPage implements OnInit {
  id = input.required<string>();
  private api = inject(Api);
  private toast = inject(ToastService);
  protected tabs: Tab[] = ['subscriptions', 'payments', 'attendance'];
  protected tab = signal<Tab>('subscriptions');
  protected m = signal<Member | null>(null);
  protected subs = signal<Subscription[]>([]);
  protected current = signal<Subscription | null>(null);
  protected payments = signal<Page<Payment> | null>(null);
  protected attendance = signal<Page<Attendance> | null>(null);
  protected subOpen = signal(false);
  protected payOpen = signal(false);
  protected resetOpen = signal(false);
  protected renewFrom = signal<Subscription | null>(null);
  protected payFor = signal<Subscription | null>(null);
  newPassword = '';

  ngOnInit() {
    this.reload();
  }

  reload() {
    this.api.get<Member>(`/members/${this.id()}`).subscribe((m) => this.m.set(m));
    this.api.get<Page<Subscription>>('/subscriptions', { member_id: this.id(), page_size: 100 }).subscribe((p) => {
      this.subs.set(p.items);
      const pick =
        p.items.find((s) => s.state === 'active') ??
        p.items.find((s) => s.state === 'upcoming') ??
        p.items.find((s) => s.state === 'expired') ??
        null;
      this.current.set(pick);
    });
    this.loadPayments(1);
    this.loadAttendance(1);
  }

  onPhoto(updated: Member) {
    this.m.update((m) => (m ? { ...m, photo_url: updated.photo_url } : m));
    this.toast.ok(updated.photo_url ? 'Photo updated' : 'Photo removed');
  }

  loadPayments(page: number) {
    this.api.get<Page<Payment>>('/payments', { member_id: this.id(), page, page_size: 10 }).subscribe((p) => this.payments.set(p));
  }

  loadAttendance(page: number) {
    this.api.get<Page<Attendance>>('/attendance', { member_id: this.id(), page, page_size: 10 }).subscribe((p) => this.attendance.set(p));
  }

  openAssign() {
    this.renewFrom.set(null);
    this.subOpen.set(true);
  }

  openRenew(s: Subscription) {
    this.renewFrom.set(s);
    this.subOpen.set(true);
  }

  afterSave(msg: string) {
    this.subOpen.set(false);
    this.payOpen.set(false);
    this.toast.ok(msg);
    this.reload();
  }

  subAction(s: Subscription, el: HTMLSelectElement) {
    const v = el.value;
    el.value = '';
    if (v === 'renew') return this.openRenew(s);
    if (v === 'pay') {
      this.payFor.set(s);
      return this.payOpen.set(true);
    }
    if (v === 'cancelled' && !confirm('Cancel this subscription? The record is kept for history.')) return;
    this.api.post(`/subscriptions/${s.id}/status`, { status: v }).subscribe({
      next: () => this.afterSave(`Subscription ${v === 'active' ? 'reactivated' : v}`),
      error: (e) => this.toast.error(errorMessage(e)),
    });
  }

  toggleStatus() {
    const m = this.m()!;
    const status = m.status === 'active' ? 'inactive' : 'active';
    if (status === 'inactive' && !confirm(`Deactivate ${m.full_name}? They will be signed out and unable to check in.`)) return;
    this.api.post<Member>(`/members/${m.id}/status`, { status }).subscribe({
      next: () => this.afterSave(`Account ${status === 'active' ? 'activated' : 'deactivated'}`),
      error: (e) => this.toast.error(errorMessage(e)),
    });
  }

  resetPassword() {
    this.api.post(`/members/${this.id()}/reset-password`, { new_password: this.newPassword }).subscribe({
      next: () => {
        this.toast.show(`Password reset. Share it with the member: ${this.newPassword}`, 'ok', 20000);
        this.resetOpen.set(false);
        this.newPassword = '';
      },
      error: (e) => this.toast.error(errorMessage(e)),
    });
  }

  manualCheckIn() {
    this.api.post('/attendance/manual', { member_id: Number(this.id()) }).subscribe({
      next: () => {
        this.toast.ok('Attendance recorded');
        this.loadAttendance(1);
      },
      error: (e) => this.toast.error(errorMessage(e)),
    });
  }
}
