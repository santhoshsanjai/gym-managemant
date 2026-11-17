import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Api, downloadBlob, errorMessage } from '../../core/api.service';
import { ToastService } from '../../core/toast.service';

@Component({
  selector: 'app-reports',
  imports: [FormsModule],
  template: `
    <div class="page-head"><h1>Reports</h1></div>
    <div class="grid two">
      <section class="card">
        <h2>Monthly payments</h2>
        <p class="muted">
          Payment details with member, package and subscription information for the selected month (by payment date). Includes a summary
          sheet.
        </p>
        <div class="form cols">
          <div class="field"><label for="rm">Month</label><input id="rm" type="month" [(ngModel)]="month" /></div>
          <div class="field">
            <label for="rs">Payment status</label>
            <select id="rs" [(ngModel)]="status">
              <option value="paid">Paid only (revenue)</option>
              <option value="all">All statuses</option>
              <option value="pending">Pending</option>
              <option value="failed">Failed</option>
              <option value="refunded">Refunded</option>
            </select>
          </div>
        </div>
        <button class="btn primary" type="button" style="margin-top:1rem" [disabled]="busy() || !month" (click)="payments()">
          Download .xlsx
        </button>
      </section>
      <section class="card">
        <h2>Members</h2>
        <p class="muted">All members with contact details, trainer, account status, current package and expiry date.</p>
        <button class="btn primary" type="button" [disabled]="busy()" (click)="members()">Download .xlsx</button>
      </section>
    </div>
  `,
})
export class ReportsPage {
  private api = inject(Api);
  private toast = inject(ToastService);
  protected busy = signal(false);
  month = new Date().toISOString().slice(0, 7);
  status = 'paid';

  payments() {
    const [year, month] = this.month.split('-').map(Number);
    this.run(this.api.blob('/reports/payments.xlsx', { year, month, status: this.status }), `payments-${this.month}.xlsx`);
  }

  members() {
    this.run(this.api.blob('/reports/members.xlsx'), `members-${new Date().toLocaleDateString('en-CA')}.xlsx`);
  }

  private run(obs: ReturnType<Api['blob']>, name: string) {
    this.busy.set(true);
    obs.subscribe({
      next: (b) => {
        this.busy.set(false);
        downloadBlob(b, name);
      },
      error: (e) => {
        this.busy.set(false);
        this.toast.error(errorMessage(e));
      },
    });
  }
}
