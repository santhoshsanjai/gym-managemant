import { Component, OnInit, inject, input, output, signal } from '@angular/core';
import { CurrencyPipe } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Api, errorMessage } from '../core/api.service';
import { PAYMENT_METHODS, PAYMENT_STATUSES, Package, Subscription } from '../core/models';
import { DurationPipe, HumanizePipe } from './pipes';

/** Assign a package to a member, or renew an existing subscription, with an
 * optional payment recorded in the same step. */
@Component({
  selector: 'app-subscription-form',
  imports: [ReactiveFormsModule, CurrencyPipe, DurationPipe, HumanizePipe],
  template: `
    @if (error()) {
      <div class="alert error" role="alert">{{ error() }}</div>
    }
    <form class="form" [formGroup]="form" (ngSubmit)="submit()">
      <div class="field">
        <label for="pkg">Package</label>
        <select id="pkg" formControlName="package_id" (change)="onPackage()">
          <option [ngValue]="null" disabled>Select a package</option>
          @for (p of packages(); track p.id) {
            <option [ngValue]="p.id">{{ p.name }} · {{ p | duration }} · {{ p.price | currency: 'INR' : 'symbol' : '1.0-2' }}</option>
          }
        </select>
      </div>
      <div class="form cols">
        <div class="field">
          <label for="start">Start date</label>
          <input id="start" type="date" formControlName="start_date" />
          <span class="hint">{{ renewFrom() ? 'Leave empty to continue after the current period.' : 'Leave empty for today.' }}</span>
        </div>
        <div class="field">
          <label for="amount">Amount agreed (₹)</label>
          <input id="amount" type="number" min="0" step="0.01" formControlName="amount" />
        </div>
      </div>
      <div class="field">
        <label for="notes">Notes</label>
        <input id="notes" formControlName="notes" />
      </div>
      <label style="display:flex;gap:.5rem;align-items:center">
        <input type="checkbox" formControlName="record_payment" style="width:auto" /> Record payment now
      </label>
      @if (form.value.record_payment) {
        <div class="form cols">
          <div class="field">
            <label for="method">Method</label>
            <select id="method" formControlName="method">
              @for (m of methods; track m) {
                <option [value]="m">{{ m | humanize }}</option>
              }
            </select>
          </div>
          <div class="field">
            <label for="pstatus">Status</label>
            <select id="pstatus" formControlName="pay_status">
              @for (s of statuses; track s) {
                <option [value]="s">{{ s | humanize }}</option>
              }
            </select>
          </div>
          <div class="field">
            <label for="paid">Amount paid (₹)</label>
            <input id="paid" type="number" min="0.01" step="0.01" formControlName="paid_amount" placeholder="Same as agreed" />
          </div>
          <div class="field">
            <label for="ref">Reference</label>
            <input id="ref" formControlName="reference" placeholder="UPI / receipt no." />
          </div>
        </div>
      }
      <div class="actions">
        <button class="btn primary" type="submit" [disabled]="form.invalid || busy()">
          {{ renewFrom() ? 'Renew' : 'Assign package' }}
        </button>
        <button class="btn" type="button" (click)="cancelled.emit()">Cancel</button>
      </div>
    </form>
  `,
})
export class SubscriptionForm implements OnInit {
  memberId = input.required<number>();
  renewFrom = input<Subscription | null>(null);
  saved = output<Subscription>();
  cancelled = output<void>();

  private api = inject(Api);
  protected methods = PAYMENT_METHODS;
  protected statuses = PAYMENT_STATUSES;
  protected packages = signal<Package[]>([]);
  protected busy = signal(false);
  protected error = signal('');
  protected form = inject(FormBuilder).group({
    package_id: [null as number | null, Validators.required],
    start_date: [''],
    amount: [null as number | null, Validators.min(0)],
    notes: [''],
    record_payment: [true],
    method: ['cash'],
    pay_status: ['paid'],
    paid_amount: [null as number | null],
    reference: [''],
  });

  ngOnInit() {
    this.api.get<Package[]>('/packages', { include_inactive: false }).subscribe((ps) => {
      this.packages.set(ps);
      const prev = this.renewFrom();
      if (prev && ps.some((p) => p.id === prev.package_id)) {
        this.form.patchValue({ package_id: prev.package_id });
        this.onPackage();
      }
    });
  }

  onPackage() {
    const p = this.packages().find((x) => x.id === this.form.value.package_id);
    if (p) this.form.patchValue({ amount: Number(p.price) });
  }

  submit() {
    const v = this.form.getRawValue();
    const body: any = {
      package_id: v.package_id,
      start_date: v.start_date || null,
      amount: v.amount,
      notes: v.notes || null,
      payment: v.record_payment
        ? { method: v.method, status: v.pay_status, amount: v.paid_amount || null, reference: v.reference || null }
        : null,
    };
    const prev = this.renewFrom();
    const req = prev
      ? this.api.post<Subscription>(`/subscriptions/${prev.id}/renew`, body)
      : this.api.post<Subscription>('/subscriptions', { ...body, member_id: this.memberId() });
    this.busy.set(true);
    this.error.set('');
    req.subscribe({
      next: (s) => {
        this.busy.set(false);
        this.saved.emit(s);
      },
      error: (e) => {
        this.busy.set(false);
        this.error.set(errorMessage(e));
      },
    });
  }
}
