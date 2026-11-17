import { Component, OnInit, inject, signal } from '@angular/core';
import { Api } from '../../core/api.service';
import { Subscription } from '../../core/models';
import { SHARED } from '../../shared';

interface Mine {
  current: Subscription | null;
  upcoming: Subscription | null;
  latest: Subscription | null;
}

@Component({
  selector: 'app-my-subscription',
  imports: [...SHARED],
  template: `
    <div class="page-head"><h1>My subscription</h1></div>
    @if (mine(); as m) {
      @if (m.current ?? m.latest; as s) {
        <div class="card">
          <h2>{{ s.package_name }} <app-badge [value]="s.state" /></h2>
          <dl class="kv">
            <dt>Duration</dt>
            <dd>{{ s | duration }}</dd>
            <dt>Start date</dt>
            <dd>{{ s.start_date | date: 'd MMM y' }}</dd>
            <dt>Expiry date</dt>
            <dd>{{ s.expiry_date | date: 'd MMM y' }}</dd>
            <dt>Remaining</dt>
            <dd>{{ s.state === 'active' ? s.remaining_days + ' day(s)' : '—' }}</dd>
          </dl>
        </div>
      } @else {
        <div class="card"><p class="muted">You don't have a membership yet. Visit the front desk to get started.</p></div>
      }
      @if (m.upcoming; as u) {
        <div class="card">
          <h2>Next period <app-badge value="upcoming" /></h2>
          <p>{{ u.package_name }} from {{ u.start_date | date: 'd MMM y' }} to {{ u.expiry_date | date: 'd MMM y' }}</p>
        </div>
      }
    }
    <div class="card">
      <h2>History</h2>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Package</th>
              <th>Start</th>
              <th>Expiry</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            @for (s of history(); track s.id) {
              <tr>
                <td>{{ s.package_name }}</td>
                <td>{{ s.start_date | date: 'd MMM y' }}</td>
                <td>{{ s.expiry_date | date: 'd MMM y' }}</td>
                <td><app-badge [value]="s.state" /></td>
              </tr>
            } @empty {
              <tr>
                <td colspan="4" class="empty">No history yet.</td>
              </tr>
            }
          </tbody>
        </table>
      </div>
      <p class="muted small" style="margin-bottom:0">Renewals and package changes are handled at the front desk.</p>
    </div>
  `,
})
export class MySubscriptionPage implements OnInit {
  private api = inject(Api);
  protected mine = signal<Mine | null>(null);
  protected history = signal<Subscription[]>([]);

  ngOnInit() {
    this.api.get<Mine>('/me/subscription').subscribe((m) => this.mine.set(m));
    this.api.get<Subscription[]>('/me/subscriptions').subscribe((h) => this.history.set(h));
  }
}
