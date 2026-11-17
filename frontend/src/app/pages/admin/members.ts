import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { Api, downloadBlob } from '../../core/api.service';
import { Member, Page, Trainer } from '../../core/models';
import { SHARED } from '../../shared';

@Component({
  selector: 'app-members',
  imports: [FormsModule, RouterLink, ...SHARED],
  template: `
    <div class="page-head">
      <h1>Members</h1>
      <span class="spacer"></span>
      <button class="btn" type="button" (click)="export()">Export .xlsx</button>
      <a class="btn primary" routerLink="/admin/members/new">+ New member</a>
    </div>
    <div class="filters">
      <input
        class="grow"
        type="search"
        placeholder="Search name, mobile, email or GYM00001"
        [(ngModel)]="q"
        (ngModelChange)="debounced()"
        aria-label="Search members"
      />
      <select [(ngModel)]="membership" (ngModelChange)="load(1)" aria-label="Membership">
        <option value="">All memberships</option>
        <option value="active">Active membership</option>
        <option value="expired">Expired membership</option>
        <option value="none">Never subscribed</option>
      </select>
      <select [(ngModel)]="status" (ngModelChange)="load(1)" aria-label="Account status">
        <option value="">Any account status</option>
        <option value="active">Account active</option>
        <option value="inactive">Account inactive</option>
      </select>
      <select [(ngModel)]="trainerId" (ngModelChange)="load(1)" aria-label="Trainer">
        <option value="">Any trainer</option>
        @for (t of trainers(); track t.id) {
          <option [value]="t.id">{{ t.full_name }}</option>
        }
      </select>
    </div>
    <div class="card">
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Member</th>
              <th>Mobile</th>
              <th class="hide-sm">Package</th>
              <th>Membership</th>
              <th class="hide-sm">Expiry</th>
              <th class="hide-sm">Account</th>
            </tr>
          </thead>
          <tbody>
            @for (m of page()?.items; track m.id) {
              <tr class="clickable" (click)="open(m)" tabindex="0" (keydown.enter)="open(m)">
                <td>
                  <div class="with-avatar">
                    <app-avatar [name]="m.full_name" [src]="m.photo_url" [size]="36" />
                    <div>
                      <strong>{{ m.full_name }}</strong>
                      <div class="muted small">{{ m.member_code }}</div>
                    </div>
                  </div>
                </td>
                <td>{{ m.mobile }}</td>
                <td class="hide-sm">{{ m.current_package_name || '—' }}</td>
                <td><app-badge [value]="m.membership_state" /></td>
                <td class="hide-sm">{{ m.current_expiry_date ? (m.current_expiry_date | date: 'd MMM y') : '—' }}</td>
                <td class="hide-sm"><app-badge [value]="m.status" /></td>
              </tr>
            } @empty {
              <tr>
                <td colspan="6" class="empty">{{ page() ? 'No members match these filters.' : 'Loading…' }}</td>
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
export class MembersPage implements OnInit {
  private api = inject(Api);
  private router = inject(Router);
  private route = inject(ActivatedRoute);
  protected page = signal<Page<Member> | null>(null);
  protected trainers = signal<Trainer[]>([]);
  q = '';
  membership = '';
  status = '';
  trainerId = '';
  private timer?: ReturnType<typeof setTimeout>;

  ngOnInit() {
    this.membership = this.route.snapshot.queryParamMap.get('membership') ?? '';
    this.api.get<Page<Trainer>>('/trainers', { page_size: 200 }).subscribe((p) => this.trainers.set(p.items));
    this.load(1);
  }

  debounced() {
    clearTimeout(this.timer);
    this.timer = setTimeout(() => this.load(1), 300);
  }

  load(page: number) {
    this.api
      .get<Page<Member>>('/members', {
        page,
        page_size: 20,
        q: this.q,
        membership: this.membership,
        status: this.status,
        trainer_id: this.trainerId,
      })
      .subscribe((p) => this.page.set(p));
  }

  open(m: Member) {
    this.router.navigate(['/admin/members', m.id]);
  }

  export() {
    this.api.blob('/reports/members.xlsx').subscribe((b) => downloadBlob(b, `members-${new Date().toLocaleDateString('en-CA')}.xlsx`));
  }
}
