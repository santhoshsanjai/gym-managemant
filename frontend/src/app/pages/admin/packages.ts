import { Component, OnInit, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Api, errorMessage } from '../../core/api.service';
import { Package } from '../../core/models';
import { ToastService } from '../../core/toast.service';
import { SHARED } from '../../shared';

@Component({
  selector: 'app-packages',
  imports: [ReactiveFormsModule, ...SHARED],
  template: `
    <div class="page-head">
      <h1>Packages</h1>
      <span class="spacer"></span>
      <button class="btn primary" type="button" (click)="edit(null)">+ New package</button>
    </div>
    <div class="card">
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Duration</th>
              <th>Price</th>
              <th class="hide-sm">Description</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            @for (p of packages(); track p.id) {
              <tr>
                <td>
                  <strong>{{ p.name }}</strong>
                </td>
                <td>{{ p | duration }}</td>
                <td class="mono">{{ p.price | currency: 'INR' : 'symbol' : '1.0-2' }}</td>
                <td class="hide-sm muted">{{ p.description || '—' }}</td>
                <td><app-badge [value]="p.is_active ? 'active' : 'inactive'" /></td>
                <td class="right actions" style="justify-content:flex-end">
                  <button class="btn sm" type="button" (click)="edit(p)">Edit</button>
                  <button class="btn sm" type="button" (click)="toggle(p)">{{ p.is_active ? 'Deactivate' : 'Activate' }}</button>
                </td>
              </tr>
            } @empty {
              <tr>
                <td colspan="6" class="empty">No packages yet. Create one to start assigning memberships.</td>
              </tr>
            }
          </tbody>
        </table>
      </div>
      <p class="muted small" style="margin-bottom:0">
        Editing a package doesn't change existing subscriptions. Deactivated packages can't be assigned but stay in history.
      </p>
    </div>

    <app-modal [title]="editing() ? 'Edit package' : 'New package'" [open]="open()" (closed)="open.set(false)">
      @if (error()) {
        <div class="alert error">{{ error() }}</div>
      }
      <form class="form cols" [formGroup]="form" (ngSubmit)="save()">
        <div class="field full"><label for="pn">Name *</label><input id="pn" formControlName="name" /></div>
        <div class="field"><label for="pv">Duration *</label><input id="pv" type="number" min="1" formControlName="duration_value" /></div>
        <div class="field">
          <label for="pu">Unit *</label>
          <select id="pu" formControlName="duration_unit">
            <option value="months">Months</option>
            <option value="days">Days</option>
          </select>
        </div>
        <div class="field">
          <label for="pp">Price (₹) *</label><input id="pp" type="number" min="0" step="0.01" formControlName="price" />
        </div>
        <div class="field full"><label for="pd">Description</label><textarea id="pd" formControlName="description"></textarea></div>
        <div class="field full actions"><button class="btn primary" type="submit" [disabled]="form.invalid">Save</button></div>
      </form>
    </app-modal>
  `,
})
export class PackagesPage implements OnInit {
  private api = inject(Api);
  private toast = inject(ToastService);
  protected packages = signal<Package[]>([]);
  protected open = signal(false);
  protected editing = signal<Package | null>(null);
  protected error = signal('');
  protected form = inject(FormBuilder).group({
    name: ['', Validators.required],
    duration_value: [1, [Validators.required, Validators.min(1)]],
    duration_unit: ['months', Validators.required],
    price: [null as number | null, [Validators.required, Validators.min(0)]],
    description: [''],
  });

  ngOnInit() {
    this.load();
  }

  load() {
    this.api.get<Package[]>('/packages').subscribe((p) => this.packages.set(p));
  }

  edit(p: Package | null) {
    this.editing.set(p);
    this.error.set('');
    this.form.reset({ duration_value: 1, duration_unit: 'months' });
    if (p) this.form.patchValue({ ...p, price: Number(p.price) });
    this.open.set(true);
  }

  save() {
    const v = this.form.getRawValue();
    const body = { ...v, description: v.description || null };
    const p = this.editing();
    const req = p ? this.api.patch(`/packages/${p.id}`, body) : this.api.post('/packages', body);
    req.subscribe({
      next: () => {
        this.open.set(false);
        this.toast.ok('Package saved');
        this.load();
      },
      error: (e) => this.error.set(errorMessage(e)),
    });
  }

  toggle(p: Package) {
    this.api.patch(`/packages/${p.id}`, { is_active: !p.is_active }).subscribe({
      next: () => this.load(),
      error: (e) => this.toast.error(errorMessage(e)),
    });
  }
}
