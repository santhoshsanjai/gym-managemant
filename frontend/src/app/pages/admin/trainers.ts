import { Component, OnInit, inject, signal } from '@angular/core';
import { FormBuilder, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { Api, errorMessage } from '../../core/api.service';
import { Page, Trainer } from '../../core/models';
import { ToastService } from '../../core/toast.service';
import { SHARED } from '../../shared';

@Component({
  selector: 'app-trainers',
  imports: [ReactiveFormsModule, FormsModule, ...SHARED],
  template: `
    <div class="page-head">
      <h1>Trainers</h1>
      <span class="spacer"></span>
      <button class="btn primary" type="button" (click)="edit(null)">+ Add trainer</button>
    </div>
    <div class="filters">
      <input
        class="grow"
        type="search"
        placeholder="Search name or mobile"
        [(ngModel)]="q"
        (ngModelChange)="load(1)"
        aria-label="Search trainers"
      />
      <select [(ngModel)]="status" (ngModelChange)="load(1)" aria-label="Status">
        <option value="">All</option>
        <option value="active">Active</option>
        <option value="inactive">Inactive</option>
      </select>
    </div>
    <div class="card">
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Trainer</th>
              <th>Mobile</th>
              <th class="hide-sm">Specialization</th>
              <th class="hide-sm">Experience</th>
              <th>Members</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            @for (t of page()?.items; track t.id) {
              <tr>
                <td>
                  <strong>{{ t.full_name }}</strong>
                  <div class="muted small">{{ t.trainer_code }}</div>
                </td>
                <td>{{ t.mobile }}</td>
                <td class="hide-sm">{{ t.specialization || '—' }}</td>
                <td class="hide-sm">{{ t.experience_years != null ? t.experience_years + ' yrs' : '—' }}</td>
                <td>{{ t.assigned_members }}</td>
                <td><app-badge [value]="t.status" /></td>
                <td class="right"><button class="btn sm" type="button" (click)="edit(t)">Edit</button></td>
              </tr>
            } @empty {
              <tr>
                <td colspan="7" class="empty">No trainers yet.</td>
              </tr>
            }
          </tbody>
        </table>
      </div>
      @if (page(); as p) {
        <app-pager [page]="p.page" [pageSize]="p.page_size" [total]="p.total" (pageChange)="load($event)" />
      }
    </div>

    <app-modal [title]="editing() ? 'Edit trainer' : 'Add trainer'" [open]="open()" (closed)="open.set(false)">
      @if (error()) {
        <div class="alert error">{{ error() }}</div>
      }
      <form class="form cols" [formGroup]="form" (ngSubmit)="save()">
        <div class="field full"><label for="tn">Full name *</label><input id="tn" formControlName="full_name" /></div>
        <div class="field"><label for="tm">Mobile *</label><input id="tm" type="tel" formControlName="mobile" /></div>
        <div class="field"><label for="te">Email</label><input id="te" type="email" formControlName="email" /></div>
        <div class="field">
          <label for="ts">Specialization</label><input id="ts" formControlName="specialization" placeholder="Strength, Yoga…" />
        </div>
        <div class="field">
          <label for="tx">Experience (years)</label><input id="tx" type="number" min="0" formControlName="experience_years" />
        </div>
        @if (editing()) {
          <div class="field">
            <label for="tst">Status</label>
            <select id="tst" formControlName="status">
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
            </select>
          </div>
        }
        <div class="field full"><label for="tno">Notes</label><textarea id="tno" formControlName="notes"></textarea></div>
        <div class="field full actions">
          <button class="btn primary" type="submit" [disabled]="form.invalid">Save</button>
          @if (editing(); as t) {
            <span class="spacer"></span>
            <button class="btn danger" type="button" (click)="remove(t)">Delete</button>
          }
        </div>
      </form>
    </app-modal>
  `,
})
export class TrainersPage implements OnInit {
  private api = inject(Api);
  private toast = inject(ToastService);
  protected page = signal<Page<Trainer> | null>(null);
  protected open = signal(false);
  protected editing = signal<Trainer | null>(null);
  protected error = signal('');
  q = '';
  status = '';
  protected form = inject(FormBuilder).group({
    full_name: ['', Validators.required],
    mobile: ['', [Validators.required, Validators.pattern(/^\+?[0-9]{7,15}$/)]],
    email: ['', Validators.email],
    specialization: [''],
    experience_years: [null as number | null, Validators.min(0)],
    status: ['active'],
    notes: [''],
  });

  ngOnInit() {
    this.load(1);
  }

  load(page: number) {
    this.api.get<Page<Trainer>>('/trainers', { page, q: this.q, status: this.status }).subscribe((p) => this.page.set(p));
  }

  edit(t: Trainer | null) {
    this.editing.set(t);
    this.error.set('');
    this.form.reset({ status: 'active' });
    if (t) this.form.patchValue(t as any);
    this.open.set(true);
  }

  save() {
    const v: any = Object.fromEntries(Object.entries(this.form.getRawValue()).map(([k, x]) => [k, x === '' ? null : x]));
    const t = this.editing();
    if (!t) delete v.status;
    const req = t ? this.api.patch(`/trainers/${t.id}`, v) : this.api.post('/trainers', v);
    req.subscribe({
      next: () => {
        this.open.set(false);
        this.toast.ok('Trainer saved');
        this.load(this.page()?.page ?? 1);
      },
      error: (e) => this.error.set(errorMessage(e)),
    });
  }

  remove(t: Trainer) {
    if (!confirm(`Delete ${t.full_name}?`)) return;
    this.api.delete(`/trainers/${t.id}`).subscribe({
      next: () => {
        this.open.set(false);
        this.toast.ok('Trainer deleted');
        this.load(1);
      },
      error: (e) => this.error.set(errorMessage(e)),
    });
  }
}
