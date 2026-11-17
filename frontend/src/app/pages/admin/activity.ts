import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { Api } from '../../core/api.service';
import { Page } from '../../core/models';
import { SHARED } from '../../shared';

interface AuditEntry {
  id: number;
  actor_user_id: number | null;
  actor_username: string | null;
  action: string;
  entity: string;
  entity_id: string | null;
  details: Record<string, unknown> | null;
  created_at: string;
}

const ENTITIES = ['member', 'subscription', 'payment', 'attendance', 'trainer', 'package', 'admin', 'report', 'user', 'notification'];

@Component({
  selector: 'app-activity',
  imports: [FormsModule, RouterLink, ...SHARED],
  template: `
    <div class="page-head">
      <div>
        <h1>Activity log</h1>
        <div class="sub">Who changed what, for important admin actions.</div>
      </div>
    </div>
    <div class="filters">
      <div class="field">
        <label for="ae">Record type</label>
        <select id="ae" [(ngModel)]="entity" (ngModelChange)="load(1)">
          <option value="">All</option>
          @for (e of entities; track e) {
            <option [value]="e">{{ e | humanize }}</option>
          }
        </select>
      </div>
      <div class="field"><label for="af">From</label><input id="af" type="date" [(ngModel)]="from" (ngModelChange)="load(1)" /></div>
      <div class="field"><label for="at">To</label><input id="at" type="date" [(ngModel)]="to" (ngModelChange)="load(1)" /></div>
    </div>
    <div class="card">
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>When</th>
              <th>Who</th>
              <th>Action</th>
              <th>Record</th>
              <th class="hide-sm">Details</th>
            </tr>
          </thead>
          <tbody>
            @for (r of page()?.items; track r.id) {
              <tr>
                <td>{{ r.created_at | date: 'd MMM y, h:mm a' }}</td>
                <td>{{ r.actor_username ?? '—' }}</td>
                <td>{{ r.action | humanize }}</td>
                <td>
                  @if (r.entity === 'member' && r.entity_id) {
                    <a [routerLink]="['/admin/members', r.entity_id]">Member #{{ r.entity_id }}</a>
                  } @else {
                    {{ r.entity | humanize }}{{ r.entity_id ? ' #' + r.entity_id : '' }}
                  }
                </td>
                <td class="hide-sm muted small details">{{ describe(r.details) }}</td>
              </tr>
            } @empty {
              <tr>
                <td colspan="5" class="empty">{{ page() ? 'No activity in this range.' : 'Loading…' }}</td>
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
  styles: `
    .details {
      max-width: 420px;
      overflow-wrap: anywhere;
    }
  `,
})
export class ActivityPage implements OnInit {
  private api = inject(Api);
  protected entities = ENTITIES;
  protected page = signal<Page<AuditEntry> | null>(null);
  entity = '';
  from = '';
  to = '';

  ngOnInit() {
    this.load(1);
  }

  load(page: number) {
    this.api
      .get<Page<AuditEntry>>('/audit-logs', { page, page_size: 30, entity: this.entity, date_from: this.from, date_to: this.to })
      .subscribe((p) => this.page.set(p));
  }

  describe(d: Record<string, unknown> | null): string {
    if (!d) return '';
    return Object.entries(d)
      .map(([k, v]) => `${k.replace(/_/g, ' ')}: ${typeof v === 'object' && v !== null ? JSON.stringify(v) : v}`)
      .join(' · ');
  }
}
