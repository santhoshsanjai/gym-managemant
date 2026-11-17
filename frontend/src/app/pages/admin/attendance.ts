import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { Api, errorMessage } from '../../core/api.service';
import { Attendance, Member, Page } from '../../core/models';
import { ToastService } from '../../core/toast.service';
import { SHARED } from '../../shared';

const today = () => new Date().toLocaleDateString('en-CA');

@Component({
  selector: 'app-attendance',
  imports: [FormsModule, RouterLink, ...SHARED],
  template: `
    <div class="page-head">
      <h1>Attendance</h1>
      <span class="spacer"></span>
      <a class="btn" routerLink="/admin/qr-display" target="_blank">Open gym QR display</a>
      <button class="btn primary" type="button" (click)="manualOpen.set(true)">+ Manual entry</button>
    </div>
    <div class="filters">
      <div class="field"><label for="df">From</label><input id="df" type="date" [(ngModel)]="from" (ngModelChange)="load(1)" /></div>
      <div class="field"><label for="dt">To</label><input id="dt" type="date" [(ngModel)]="to" (ngModelChange)="load(1)" /></div>
      <div class="field grow">
        <label for="mf">Member</label>
        <select id="mf" [(ngModel)]="memberId" (ngModelChange)="load(1)">
          <option value="">All members</option>
          @for (m of members(); track m.id) {
            <option [value]="m.id">{{ m.full_name }} · {{ m.member_code }}</option>
          }
        </select>
      </div>
    </div>
    <div class="card">
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Member</th>
              <th>Date</th>
              <th>Time</th>
              <th>Source</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            @for (a of page()?.items; track a.id) {
              <tr>
                <td>
                  <a [routerLink]="['/admin/members', a.member_id]">{{ a.member.full_name }}</a>
                  <div class="muted small">{{ a.member.member_code }}</div>
                </td>
                <td>{{ a.attendance_date | date: 'EEE, d MMM y' }}</td>
                <td>{{ a.checked_in_at | date: 'h:mm a' }}</td>
                <td><app-badge [value]="a.source" [text]="a.source === 'qr' ? 'QR scan' : 'Manual'" /></td>
                <td class="right"><button class="btn sm danger" type="button" (click)="remove(a)">Remove</button></td>
              </tr>
            } @empty {
              <tr>
                <td colspan="5" class="empty">No attendance in this range.</td>
              </tr>
            }
          </tbody>
        </table>
      </div>
      @if (page(); as p) {
        <app-pager [page]="p.page" [pageSize]="p.page_size" [total]="p.total" (pageChange)="load($event)" />
      }
    </div>

    <app-modal title="Manual attendance" [open]="manualOpen()" (closed)="manualOpen.set(false)">
      <form class="form" (ngSubmit)="manual()">
        <div class="field">
          <label for="mm">Member</label>
          <select id="mm" name="mm" [(ngModel)]="manualMember" required>
            <option value="">Select member</option>
            @for (m of members(); track m.id) {
              <option [value]="m.id">{{ m.full_name }} · {{ m.mobile }}</option>
            }
          </select>
        </div>
        <div class="field">
          <label for="md">Date</label>
          <input id="md" name="md" type="date" [(ngModel)]="manualDate" [max]="todayStr" />
        </div>
        <p class="muted small">
          Use this when a member can't scan (for example, a broken phone camera). The one-check-in-per-day rule still applies.
        </p>
        <div class="actions"><button class="btn primary" type="submit" [disabled]="!manualMember">Record</button></div>
      </form>
    </app-modal>
  `,
})
export class AttendancePage implements OnInit {
  private api = inject(Api);
  private toast = inject(ToastService);
  protected page = signal<Page<Attendance> | null>(null);
  protected members = signal<Member[]>([]);
  protected manualOpen = signal(false);
  protected todayStr = today();
  from = today();
  to = today();
  memberId = '';
  manualMember = '';
  manualDate = today();

  ngOnInit() {
    this.api.get<Page<Member>>('/members', { page_size: 200, status: 'active' }).subscribe((p) => this.members.set(p.items));
    this.load(1);
  }

  load(page: number) {
    this.api
      .get<Page<Attendance>>('/attendance', { page, page_size: 25, date_from: this.from, date_to: this.to, member_id: this.memberId })
      .subscribe((p) => this.page.set(p));
  }

  manual() {
    this.api.post('/attendance/manual', { member_id: Number(this.manualMember), attendance_date: this.manualDate || null }).subscribe({
      next: () => {
        this.manualOpen.set(false);
        this.toast.ok('Attendance recorded');
        this.load(1);
      },
      error: (e) => this.toast.error(errorMessage(e)),
    });
  }

  remove(a: Attendance) {
    if (!confirm(`Remove ${a.member.full_name}'s attendance on ${a.attendance_date}?`)) return;
    this.api.delete(`/attendance/${a.id}`).subscribe(() => this.load(this.page()?.page ?? 1));
  }
}
