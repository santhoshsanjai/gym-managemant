import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { Api, downloadBlob } from '../../core/api.service';
import { PAYMENT_METHODS, PAYMENT_STATUSES, Page, Payment, PaymentSummary } from '../../core/models';
import { ToastService } from '../../core/toast.service';
import { SHARED } from '../../shared';
import { PaymentForm } from '../../shared/payment-form';

@Component({
  selector: 'app-payments',
  imports: [FormsModule, RouterLink, PaymentForm, ...SHARED],
  template: `
    <div class="page-head">
      <h1>Payments</h1>
      <span class="spacer"></span>
      <button class="btn" type="button" (click)="export()">Export month (.xlsx)</button>
      <button class="btn primary" type="button" (click)="editing.set(null); open.set(true)">+ Record payment</button>
    </div>
    <div class="filters">
      <div class="field"><label for="pmo">Month</label><input id="pmo" type="month" [(ngModel)]="month" (ngModelChange)="reload()" /></div>
      <div class="field">
        <label for="pst">Status</label>
        <select id="pst" [(ngModel)]="status" (ngModelChange)="load(1)">
          <option value="">All</option>
          @for (s of statuses; track s) {
            <option [value]="s">{{ s | humanize }}</option>
          }
        </select>
      </div>
      <div class="field">
        <label for="pme">Method</label>
        <select id="pme" [(ngModel)]="method" (ngModelChange)="load(1)">
          <option value="">All</option>
          @for (m of methods; track m) {
            <option [value]="m">{{ m | humanize }}</option>
          }
        </select>
      </div>
    </div>
    @if (summary(); as s) {
      <div class="grid stats" style="margin-bottom:1rem">
        <div class="stat accent">
          <div class="label">Collected</div>
          <div class="value">{{ s.total_paid | currency: 'INR' : 'symbol' : '1.0-0' }}</div>
          <div class="small">{{ s.count_paid }} payment(s)</div>
        </div>
        <div class="stat">
          <div class="label">Pending</div>
          <div class="value">{{ s.total_pending | currency: 'INR' : 'symbol' : '1.0-0' }}</div>
          <div class="small muted">{{ s.count_pending }} payment(s)</div>
        </div>
        @for (kv of methodTotals(); track kv[0]) {
          <div class="stat">
            <div class="label">{{ kv[0] | humanize }}</div>
            <div class="value" style="font-size:1.3rem">{{ kv[1] | currency: 'INR' : 'symbol' : '1.0-0' }}</div>
          </div>
        }
      </div>
    }
    <div class="card">
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Date</th>
              <th>Member</th>
              <th>Amount</th>
              <th class="hide-sm">Method</th>
              <th class="hide-sm">Package</th>
              <th class="hide-sm">Reference</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            @for (p of page()?.items; track p.id) {
              <tr>
                <td>{{ p.payment_date | date: 'd MMM y' }}</td>
                <td>
                  <a [routerLink]="['/admin/members', p.member_id]">{{ p.member.full_name }}</a>
                </td>
                <td class="mono">{{ p.amount | currency: 'INR' : 'symbol' : '1.0-2' }}</td>
                <td class="hide-sm">{{ p.method | humanize }}</td>
                <td class="hide-sm">{{ p.package_name || '—' }}</td>
                <td class="hide-sm">{{ p.reference || '—' }}</td>
                <td><app-badge [value]="p.status" /></td>
                <td class="right"><button class="btn sm" type="button" (click)="editing.set(p); open.set(true)">Edit</button></td>
              </tr>
            } @empty {
              <tr>
                <td colspan="8" class="empty">No payments for this month.</td>
              </tr>
            }
          </tbody>
        </table>
      </div>
      @if (page(); as p) {
        <app-pager [page]="p.page" [pageSize]="p.page_size" [total]="p.total" (pageChange)="load($event)" />
      }
    </div>

    <app-modal [title]="editing() ? 'Edit payment' : 'Record payment'" [open]="open()" (closed)="open.set(false)">
      @if (open()) {
        <app-payment-form [existing]="editing()" (saved)="saved()" (cancelled)="open.set(false)" />
      }
    </app-modal>
  `,
})
export class PaymentsPage implements OnInit {
  private api = inject(Api);
  private toast = inject(ToastService);
  protected methods = PAYMENT_METHODS;
  protected statuses = PAYMENT_STATUSES;
  protected page = signal<Page<Payment> | null>(null);
  protected summary = signal<PaymentSummary | null>(null);
  protected methodTotals = signal<[string, string][]>([]);
  protected open = signal(false);
  protected editing = signal<Payment | null>(null);
  month = new Date().toISOString().slice(0, 7);
  status = '';
  method = '';

  ngOnInit() {
    this.reload();
  }

  private ym() {
    const [year, month] = this.month.split('-').map(Number);
    return { year, month };
  }

  reload() {
    if (!this.month) return;
    this.load(1);
    this.api.get<PaymentSummary>('/payments/summary', this.ym()).subscribe((s) => {
      this.summary.set(s);
      this.methodTotals.set(Object.entries(s.by_method));
    });
  }

  load(page: number) {
    this.api
      .get<Page<Payment>>('/payments', { page, ...this.ym(), status: this.status, method: this.method })
      .subscribe((p) => this.page.set(p));
  }

  saved() {
    this.open.set(false);
    this.toast.ok('Payment saved');
    this.reload();
  }

  export() {
    const { year, month } = this.ym();
    this.api
      .blob('/reports/payments.xlsx', { year, month, status: 'paid' })
      .subscribe((b) => downloadBlob(b, `payments-${year}-${String(month).padStart(2, '0')}.xlsx`));
  }
}
