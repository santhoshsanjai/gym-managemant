import { Component, OnInit, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { Api } from '../../core/api.service';
import { AdminDashboard } from '../../core/models';
import { SHARED } from '../../shared';

@Component({
  selector: 'app-admin-dashboard',
  imports: [RouterLink, ...SHARED],
  template: `
    <div class="page-head">
      <div>
        <h1>Dashboard</h1>
        @if (d(); as d) {
          <div class="sub">As of {{ d.as_of | date: 'EEEE, d MMM y' }}</div>
        }
      </div>
      <span class="spacer"></span>
      <input
        type="month"
        [value]="month()"
        (change)="setMonth($any($event.target).value)"
        aria-label="Month for revenue and new members"
        style="max-width:180px"
      />
      <a class="btn primary" routerLink="/admin/members/new">+ New member</a>
    </div>
    @if (d(); as d) {
      <div class="grid stats">
        <a class="stat" routerLink="/admin/members"
          ><div class="label">Total members</div>
          <div class="value">{{ d.total_members }}</div></a
        >
        <a class="stat" routerLink="/admin/members" [queryParams]="{ membership: 'active' }"
          ><div class="label">Active members</div>
          <div class="value">{{ d.active_members }}</div></a
        >
        <a class="stat" routerLink="/admin/members" [queryParams]="{ membership: 'expired' }"
          ><div class="label">Expired members</div>
          <div class="value">{{ d.expired_members }}</div></a
        >
        <a class="stat" routerLink="/admin/attendance"
          ><div class="label">Today's attendance</div>
          <div class="value">{{ d.todays_attendance }}</div></a
        >
        <a class="stat" routerLink="/admin/trainers"
          ><div class="label">Trainers</div>
          <div class="value">{{ d.total_trainers }}</div></a
        >
        <a class="stat accent" routerLink="/admin/payments"
          ><div class="label">Revenue · {{ monthLabel() }}</div>
          <div class="value">{{ d.monthly_revenue | currency: 'INR' : 'symbol' : '1.0-0' }}</div></a
        >
        <div class="stat">
          <div class="label">New members · {{ monthLabel() }}</div>
          <div class="value">{{ d.new_members_this_month }}</div>
        </div>
      </div>

      <div class="grid two" style="margin-top:1rem">
        <section class="card">
          <h2>Upcoming expiries <span class="muted small">(next 7 days)</span></h2>
          <ul class="list">
            @for (s of d.upcoming_expiries; track s.id) {
              <li>
                <div style="flex:1">
                  <a [routerLink]="['/admin/members', s.member_id]">{{ s.member.full_name }}</a>
                  <div class="muted small">{{ s.package_name }} · {{ s.member.mobile }}</div>
                </div>
                <div class="right">
                  <div>{{ s.expiry_date | date: 'd MMM' }}</div>
                  <app-badge
                    [value]="s.remaining_days <= 1 ? 'expired' : 'pending'"
                    [text]="s.remaining_days === 1 ? 'Last day' : s.remaining_days + ' days left'"
                  />
                </div>
              </li>
            } @empty {
              <li class="muted">No memberships expire in the next week.</li>
            }
          </ul>
        </section>
        <section class="card">
          <h2>Recently expired <span class="muted small">(last 30 days, not renewed)</span></h2>
          <ul class="list">
            @for (s of d.recently_expired; track s.id) {
              <li>
                <div style="flex:1">
                  <a [routerLink]="['/admin/members', s.member_id]">{{ s.member.full_name }}</a>
                  <div class="muted small">{{ s.package_name }} · {{ s.member.mobile }}</div>
                </div>
                <div class="right">
                  <div>{{ s.expiry_date | date: 'd MMM' }}</div>
                  <app-badge value="expired" />
                </div>
              </li>
            } @empty {
              <li class="muted">Nothing expired recently.</li>
            }
          </ul>
        </section>
      </div>
    } @else {
      <p class="muted">Loading…</p>
    }
  `,
})
export class AdminDashboardPage implements OnInit {
  private api = inject(Api);
  protected d = signal<AdminDashboard | null>(null);
  protected month = signal(new Date().toISOString().slice(0, 7));
  protected monthLabel = signal('this month');

  ngOnInit() {
    this.load();
  }

  setMonth(v: string) {
    if (!v) return;
    this.month.set(v);
    this.load();
  }

  private load() {
    const [year, month] = this.month().split('-').map(Number);
    this.api.get<AdminDashboard>('/dashboard/admin', { year, month }).subscribe((d) => {
      this.d.set(d);
      const now = new Date();
      this.monthLabel.set(
        year === now.getFullYear() && month === now.getMonth() + 1
          ? 'this month'
          : new Date(year, month - 1, 1).toLocaleDateString('en-IN', { month: 'short', year: 'numeric' }),
      );
    });
  }
}
