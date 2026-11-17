import { Component, OnInit, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { Api } from '../../core/api.service';
import { MemberDashboard } from '../../core/models';
import { SHARED } from '../../shared';

@Component({
  selector: 'app-member-dashboard',
  imports: [RouterLink, ...SHARED],
  template: `
    @if (d(); as d) {
      <div class="page-head">
        <app-avatar [name]="d.profile.full_name" [src]="d.profile.photo_url" [size]="48" />
        <div>
          <h1>Hi, {{ d.profile.full_name.split(' ')[0] }}</h1>
          <div class="sub">{{ d.profile.member_code }} · {{ d.as_of | date: 'EEEE, d MMM' }}</div>
        </div>
      </div>

      @if (!d.current_subscription) {
        <div class="alert warn">
          @if (d.upcoming_subscription; as u) {
            Your {{ u.package_name }} membership starts on {{ u.start_date | date: 'd MMM y' }}.
          } @else {
            You don't have an active membership. Please renew at the front desk.
          }
        </div>
      } @else if (d.remaining_days <= 7) {
        <div class="alert warn">
          Your membership ends {{ d.remaining_days === 1 ? 'today' : 'in ' + d.remaining_days + ' days' }}. Renew at the front desk to keep
          access.
        </div>
      }

      <div class="card" style="text-align:center">
        @if (d.checked_in_today) {
          <div style="font-size:2.5rem" aria-hidden="true">✅</div>
          <h2 style="margin:.25rem 0">Checked in today</h2>
          <div class="muted">at {{ d.todays_checkin?.checked_in_at | date: 'h:mm a' }}</div>
        } @else {
          <h2>Ready for your workout?</h2>
          <a class="btn primary block" routerLink="/member/scan" style="font-size:1.1rem;padding:.9rem">Scan gym QR to check in</a>
        }
      </div>

      <div class="grid stats" style="margin-top:1rem">
        <div class="stat accent">
          <div class="label">Days left</div>
          <div class="value">{{ d.remaining_days }}</div>
        </div>
        <div class="stat">
          <div class="label">This month</div>
          <div class="value">{{ d.attendance_this_month }}</div>
          <div class="small muted">visits</div>
        </div>
        <div class="stat">
          <div class="label">All time</div>
          <div class="value">{{ d.total_attendance }}</div>
          <div class="small muted">visits</div>
        </div>
      </div>

      <div class="grid two" style="margin-top:1rem">
        <section class="card">
          <h2>Membership</h2>
          @if (d.current_subscription ?? d.latest_subscription; as s) {
            <dl class="kv">
              <dt>Package</dt>
              <dd>{{ s.package_name }}</dd>
              <dt>Duration</dt>
              <dd>{{ s | duration }}</dd>
              <dt>Start</dt>
              <dd>{{ s.start_date | date: 'd MMM y' }}</dd>
              <dt>Expiry</dt>
              <dd>{{ s.expiry_date | date: 'd MMM y' }}</dd>
              <dt>Status</dt>
              <dd><app-badge [value]="s.state" /></dd>
            </dl>
          } @else {
            <p class="muted">No membership yet.</p>
          }
          <a routerLink="/member/subscription" class="small">View details →</a>
        </section>
        <section class="card">
          <h2>
            Notifications
            @if (d.unread_notifications) {
              <span class="badge blue">{{ d.unread_notifications }} new</span>
            }
          </h2>
          <ul class="list">
            @for (n of d.recent_notifications; track n.id) {
              <li>
                <div>
                  <strong>{{ n.title }}</strong>
                  <div class="muted small">{{ n.created_at | date: 'd MMM, h:mm a' }}</div>
                </div>
              </li>
            } @empty {
              <li class="muted">You're all caught up.</li>
            }
          </ul>
          <a routerLink="/member/notifications" class="small">All notifications →</a>
        </section>
      </div>
    } @else {
      <p class="muted">Loading…</p>
    }
  `,
})
export class MemberDashboardPage implements OnInit {
  private api = inject(Api);
  protected d = signal<MemberDashboard | null>(null);

  ngOnInit() {
    this.api.get<MemberDashboard>('/dashboard/member').subscribe((d) => this.d.set(d));
  }
}
