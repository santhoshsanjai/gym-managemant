import { Component, OnInit, inject, input, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { Api, errorMessage } from '../../core/api.service';
import { Member, Page, Trainer } from '../../core/models';
import { ToastService } from '../../core/toast.service';

const MOBILE = /^\+?[0-9]{7,15}$/;

@Component({
  selector: 'app-member-form',
  imports: [ReactiveFormsModule, RouterLink],
  template: `
    <div class="page-head">
      <a class="btn ghost sm" [routerLink]="id() ? ['/admin/members', id()] : '/admin/members'">← Back</a>
      <h1>{{ id() ? 'Edit member' : 'Register member' }}</h1>
    </div>
    <div class="card" style="max-width:820px">
      @if (error()) {
        <div class="alert error" role="alert">{{ error() }}</div>
      }
      <form class="form cols" [formGroup]="form" (ngSubmit)="submit()">
        <div class="field">
          <label for="name">Full name *</label>
          <input id="name" formControlName="full_name" autocomplete="off" />
        </div>
        <div class="field">
          <label for="mobile">Mobile number *</label>
          <input id="mobile" type="tel" formControlName="mobile" inputmode="tel" />
          <span class="hint">Used by the member to sign in.</span>
          @if (form.controls.mobile.touched && form.controls.mobile.invalid) {
            <span class="err">Enter 7–15 digits.</span>
          }
        </div>
        <div class="field">
          <label for="email">Email</label>
          <input id="email" type="email" formControlName="email" />
        </div>
        <div class="field">
          <label for="gender">Gender</label>
          <select id="gender" formControlName="gender">
            <option [ngValue]="null">—</option>
            <option value="male">Male</option>
            <option value="female">Female</option>
            <option value="other">Other</option>
          </select>
        </div>
        <div class="field">
          <label for="dob">Date of birth</label>
          <input id="dob" type="date" formControlName="date_of_birth" />
        </div>
        <div class="field">
          <label for="join">Joining date</label>
          <input id="join" type="date" formControlName="joining_date" />
        </div>
        <div class="field">
          <label for="trainer">Assigned trainer</label>
          <select id="trainer" formControlName="trainer_id">
            <option [ngValue]="null">None</option>
            @for (t of trainers(); track t.id) {
              <option [ngValue]="t.id">{{ t.full_name }}{{ t.specialization ? ' · ' + t.specialization : '' }}</option>
            }
          </select>
        </div>
        @if (!id()) {
          <div class="field">
            <label for="photo">Photo</label>
            <input id="photo" type="file" accept="image/jpeg,image/png,image/webp" capture="user" (change)="pickPhoto($event)" />
            <span class="hint">Optional. JPEG, PNG or WebP up to 2 MB.</span>
          </div>
        }
        <div class="field full">
          <label for="addr">Address</label>
          <textarea id="addr" formControlName="address"></textarea>
        </div>
        @if (!id()) {
          <div class="field">
            <label for="pw">Initial password *</label>
            <input id="pw" type="text" formControlName="password" autocomplete="new-password" />
            <span class="hint">At least 8 characters. The member must change it on first sign-in.</span>
          </div>
        }
        <div class="field full">
          <div class="actions">
            <button class="btn primary" type="submit" [disabled]="form.invalid || busy()">
              {{ id() ? 'Save changes' : 'Register member' }}
            </button>
          </div>
        </div>
      </form>
    </div>
  `,
})
export class MemberFormPage implements OnInit {
  id = input<string>();
  private api = inject(Api);
  private router = inject(Router);
  private toast = inject(ToastService);
  protected trainers = signal<Trainer[]>([]);
  protected busy = signal(false);
  protected error = signal('');
  protected form = inject(FormBuilder).group({
    full_name: ['', [Validators.required, Validators.maxLength(150)]],
    mobile: ['', [Validators.required, Validators.pattern(MOBILE)]],
    email: ['', Validators.email],
    gender: [null as string | null],
    date_of_birth: [''],
    joining_date: [''],
    trainer_id: [null as number | null],
    address: [''],
    password: ['', [Validators.required, Validators.minLength(8)]],
  });

  ngOnInit() {
    this.api.get<Page<Trainer>>('/trainers', { status: 'active', page_size: 200 }).subscribe((p) => this.trainers.set(p.items));
    if (this.id()) {
      this.form.controls.password.disable();
      this.api.get<Member>(`/members/${this.id()}`).subscribe((m) => this.form.patchValue(m as any));
    } else {
      this.form.patchValue({ password: suggestPassword() });
    }
  }

  private photo: File | null = null;

  pickPhoto(ev: Event) {
    const f = (ev.target as HTMLInputElement).files?.[0] ?? null;
    if (f && f.size > 2 * 1024 * 1024) {
      this.toast.error('That photo is larger than 2 MB.');
      (ev.target as HTMLInputElement).value = '';
      return;
    }
    this.photo = f;
  }

  submit() {
    const raw = this.form.getRawValue();
    const body: any = Object.fromEntries(Object.entries(raw).map(([k, v]) => [k, v === '' ? null : v]));
    const req = this.id()
      ? this.api.patch<Member>(`/members/${this.id()}`, { ...body, password: undefined })
      : this.api.post<Member>('/members', body);
    this.busy.set(true);
    this.error.set('');
    req.subscribe({
      next: (m) => {
        if (!this.id() && this.photo) {
          this.api.upload(`/members/${m.id}/photo`, this.photo).subscribe({
            error: (e) => this.toast.error(`Member saved, but the photo upload failed: ${errorMessage(e)}`),
          });
        }
        if (this.id()) this.toast.ok('Member updated');
        else this.toast.show(`Member ${m.member_code} registered. Initial password: ${raw.password}`, 'ok', 20000);
        this.router.navigate(['/admin/members', m.id]);
      },
      error: (e) => {
        this.busy.set(false);
        this.error.set(errorMessage(e));
      },
    });
  }
}

function suggestPassword(): string {
  const chars = 'abcdefghjkmnpqrstuvwxyz23456789';
  const arr = new Uint32Array(10);
  crypto.getRandomValues(arr);
  return Array.from(arr, (n) => chars[n % chars.length]).join('');
}
