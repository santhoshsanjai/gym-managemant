import { Component, inject, input, output, signal, OnInit } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Api, errorMessage } from '../core/api.service';
import { Member, PAYMENT_METHODS, PAYMENT_STATUSES, Page, Payment, Subscription } from '../core/models';
import { MemberPicker } from './member-picker';
import { HumanizePipe } from './pipes';

/** Record (or correct) a manual payment. */
@Component({
  selector: 'app-payment-form',
  imports: [ReactiveFormsModule, HumanizePipe, MemberPicker],
  template: `
    @if (error()) {
      <div class="alert error" role="alert">{{ error() }}</div>
    }
    <form class="form" [formGroup]="form" (ngSubmit)="submit()">
      @if (!memberId() && !existing()) {
        <div class="field">
          <label for="msearch">Member</label>
          <app-member-picker inputId="msearch" (picked)="onMember($event)" />
        </div>
      }
      @if (!existing()) {
        <div class="field">
          <label for="sub">Subscription (optional)</label>
          <select id="sub" formControlName="subscription_id">
            <option [ngValue]="null">Not linked</option>
            @for (s of subs(); track s.id) {
              <option [ngValue]="s.id">{{ s.package_name }} · {{ s.start_date }} → {{ s.expiry_date }} ({{ s.state }})</option>
            }
          </select>
        </div>
      }
      <div class="form cols">
        <div class="field">
          <label for="amt">Amount (₹)</label>
          <input id="amt" type="number" min="0.01" step="0.01" formControlName="amount" />
        </div>
        <div class="field">
          <label for="pdate">Payment date</label>
          <input id="pdate" type="date" formControlName="payment_date" />
        </div>
        <div class="field">
          <label for="pm">Method</label>
          <select id="pm" formControlName="method">
            @for (m of methods; track m) {
              <option [value]="m">{{ m | humanize }}</option>
            }
          </select>
        </div>
        <div class="field">
          <label for="ps">Status</label>
          <select id="ps" formControlName="status">
            @for (s of statuses; track s) {
              <option [value]="s">{{ s | humanize }}</option>
            }
          </select>
        </div>
      </div>
      <div class="field">
        <label for="pref">Reference</label>
        <input id="pref" formControlName="reference" placeholder="UPI transaction ID, receipt no." />
      </div>
      <div class="field">
        <label for="pnotes">Notes</label>
        <input id="pnotes" formControlName="notes" />
      </div>
      <div class="actions">
        <button class="btn primary" type="submit" [disabled]="form.invalid || busy()">
          {{ existing() ? 'Save changes' : 'Record payment' }}
        </button>
        <button class="btn" type="button" (click)="cancelled.emit()">Cancel</button>
      </div>
    </form>
  `,
})
export class PaymentForm implements OnInit {
  memberId = input<number | null>(null);
  subscription = input<Subscription | null>(null);
  existing = input<Payment | null>(null);
  saved = output<Payment>();
  cancelled = output<void>();

  private api = inject(Api);
  protected methods = PAYMENT_METHODS;
  protected statuses = PAYMENT_STATUSES;
  protected subs = signal<Subscription[]>([]);
  protected busy = signal(false);
  protected error = signal('');
  protected form = inject(FormBuilder).group({
    member_id: [null as number | null, Validators.required],
    subscription_id: [null as number | null],
    amount: [null as number | null, [Validators.required, Validators.min(0.01)]],
    payment_date: [new Date().toLocaleDateString('en-CA')],
    method: ['cash', Validators.required],
    status: ['paid', Validators.required],
    reference: [''],
    notes: [''],
  });

  ngOnInit() {
    const ex = this.existing();
    if (ex) {
      this.form.patchValue({ ...ex, amount: Number(ex.amount), member_id: ex.member_id } as any);
      return;
    }
    if (this.memberId()) {
      this.form.patchValue({ member_id: this.memberId() });
      this.loadSubs();
    }
    const s = this.subscription();
    if (s) {
      const due = Math.max(0, Number(s.amount) - Number(s.amount_paid));
      this.form.patchValue({ subscription_id: s.id, amount: due || null });
    }
  }

  onMember(m: Member | null) {
    this.form.patchValue({ member_id: m?.id ?? null, subscription_id: null });
    this.subs.set([]);
    this.loadSubs();
  }

  loadSubs() {
    const id = this.form.value.member_id;
    if (!id) return;
    this.api.get<Page<Subscription>>('/subscriptions', { member_id: id, page_size: 50 }).subscribe((p) => this.subs.set(p.items));
  }

  submit() {
    const v = this.form.getRawValue();
    const body: any = { ...v, reference: v.reference || null, notes: v.notes || null, payment_date: v.payment_date || null };
    const ex = this.existing();
    const req = ex
      ? this.api.patch<Payment>(`/payments/${ex.id}`, {
          amount: body.amount,
          payment_date: body.payment_date,
          method: body.method,
          status: body.status,
          reference: body.reference,
          notes: body.notes,
        })
      : this.api.post<Payment>('/payments', body);
    this.busy.set(true);
    req.subscribe({
      next: (p) => {
        this.busy.set(false);
        this.saved.emit(p);
      },
      error: (e) => {
        this.busy.set(false);
        this.error.set(errorMessage(e));
      },
    });
  }
}
