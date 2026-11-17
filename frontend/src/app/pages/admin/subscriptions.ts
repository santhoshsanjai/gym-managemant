import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { Api } from '../../core/api.service';
import { Package, Page, Subscription } from '../../core/models';
import { SHARED } from '../../shared';

@Component({
  selector: 'app-subscriptions',
  imports: [FormsModule, RouterLink, ...SHARED],
  template: `
    <div class="page-head"><h1>Subscriptions</h1></div>
    <div class="filters">
      <select [(ngModel)]="state" (ngModelChange)="load(1)" aria-label="State">
        <option value="">All states</option>
        <option value="active">Active</option>
        <option value="upcoming">Upcoming</option>
        <option value="expired">Expired</option>
        <option value="suspended">Suspended</option>
        <option value="cancelled">Cancelled</option>
      </select>
      <select [(ngModel)]="expiring" (ngModelChange)="load(1)" aria-label="Expiring within">
        <option value="">Any expiry</option>
        <option value="7">Expiring in 7 days</option>
        <option value="15">Expiring in 15 days</option>
        <option value="30">Expiring in 30 days</option>
      </select>
      <select [(ngModel)]="packageId" (ngModelChange)="load(1)" aria-label="Package">
        <option value="">All packages</option>
        @for (p of packages(); track p.id) {
          <option [value]="p.id">{{ p.name }}</option>
        }
      </select>
    </div>
    <div class="card">
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Member</th>
              <th>Package</th>
              <th>Start</th>
              <th>Expiry</th>
              <th class="hide-sm">Amount</th>
              <th class="hide-sm">Paid</th>
              <th>State</th>
            </tr>
          </thead>
          <tbody>
            @for (s of page()?.items; track s.id) {
              <tr>
                <td>
                  <a [routerLink]="['/admin/members', s.member_id]">{{ s.member.full_name }}</a>
                  <div class="muted small">{{ s.member.member_code }}</div>
                </td>
                <td>{{ s.package_name }}</td>
                <td>{{ s.start_date | date: 'd MMM y' }}</td>
                <td>{{ s.expiry_date | date: 'd MMM y' }}</td>
                <td class="hide-sm mono">{{ s.amount | currency: 'INR' : 'symbol' : '1.0-2' }}</td>
                <td class="hide-sm mono">{{ s.amount_paid | currency: 'INR' : 'symbol' : '1.0-2' }}</td>
                <td>
                  <app-badge [value]="s.state" />
                  @if (s.state === 'active') {
                    <div class="muted small">{{ s.remaining_days }}d left</div>
                  }
                </td>
              </tr>
            } @empty {
              <tr>
                <td colspan="7" class="empty">No subscriptions match.</td>
              </tr>
            }
          </tbody>
        </table>
      </div>
      @if (page(); as p) {
        <app-pager [page]="p.page" [pageSize]="p.page_size" [total]="p.total" (pageChange)="load($event)" />
      }
    </div>
  `,
})
export class SubscriptionsPage implements OnInit {
  private api = inject(Api);
  protected page = signal<Page<Subscription> | null>(null);
  protected packages = signal<Package[]>([]);
  state = '';
  expiring = '';
  packageId = '';

  ngOnInit() {
    this.api.get<Package[]>('/packages').subscribe((p) => this.packages.set(p));
    this.load(1);
  }

  load(page: number) {
    this.api
      .get<Page<Subscription>>('/subscriptions', {
        page,
        state: this.state,
        expiring_within_days: this.expiring,
        package_id: this.packageId,
      })
      .subscribe((p) => this.page.set(p));
  }
}
