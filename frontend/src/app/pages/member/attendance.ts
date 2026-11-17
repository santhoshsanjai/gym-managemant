import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Api } from '../../core/api.service';
import { Attendance, Page } from '../../core/models';
import { SHARED } from '../../shared';

type MyPage = Page<Attendance> & { total_all_time: number };

@Component({
  selector: 'app-my-attendance',
  imports: [FormsModule, ...SHARED],
  template: `
    <div class="page-head">
      <h1>My attendance</h1>
      <span class="spacer"></span>
      <input type="month" [(ngModel)]="month" (ngModelChange)="load(1)" aria-label="Month" style="max-width:180px" />
    </div>
    @if (page(); as p) {
      <div class="grid stats" style="margin-bottom:1rem">
        <div class="stat accent">
          <div class="label">Visits this month</div>
          <div class="value">{{ p.total }}</div>
        </div>
        <div class="stat">
          <div class="label">All time</div>
          <div class="value">{{ p.total_all_time }}</div>
        </div>
      </div>
      <div class="card">
        <ul class="list">
          @for (a of p.items; track a.id) {
            <li>
              <div style="flex:1">
                <strong>{{ a.attendance_date | date: 'EEEE, d MMM y' }}</strong>
              </div>
              <span class="muted">{{ a.checked_in_at | date: 'h:mm a' }}</span>
            </li>
          } @empty {
            <li class="muted">No visits recorded in this month.</li>
          }
        </ul>
        <app-pager [page]="p.page" [pageSize]="p.page_size" [total]="p.total" (pageChange)="load($event)" />
      </div>
    }
  `,
})
export class MyAttendancePage implements OnInit {
  private api = inject(Api);
  protected page = signal<MyPage | null>(null);
  month = new Date().toISOString().slice(0, 7);

  ngOnInit() {
    this.load(1);
  }

  load(page: number) {
    const [year, month] = (this.month || new Date().toISOString().slice(0, 7)).split('-').map(Number);
    this.api.get<MyPage>('/me/attendance', { page, page_size: 31, year, month }).subscribe((p) => this.page.set(p));
  }
}
