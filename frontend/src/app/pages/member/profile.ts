import { Component, OnInit, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { Api, errorMessage } from '../../core/api.service';
import { Member } from '../../core/models';
import { ToastService } from '../../core/toast.service';
import { SHARED } from '../../shared';
import { PhotoUpload } from '../../shared/photo-upload';

@Component({
  selector: 'app-profile',
  imports: [ReactiveFormsModule, RouterLink, PhotoUpload, ...SHARED],
  template: `
    <div class="page-head">
      <h1>Profile</h1>
      <span class="spacer"></span>
      <a class="btn" routerLink="/change-password">Change password</a>
    </div>
    @if (m(); as m) {
      <div class="grid two">
        <section class="card">
          <h2>Account</h2>
          @if (can('photo_url')) {
            <app-photo-upload
              [name]="m.full_name"
              [url]="m.photo_url"
              uploadPath="/me/profile/photo"
              removePath="/me/profile/photo"
              (changed)="onPhoto($event)"
            />
          } @else {
            <app-avatar [name]="m.full_name" [src]="m.photo_url" [size]="88" />
          }
          <div style="height:1rem"></div>
          <dl class="kv">
            <dt>Member ID</dt>
            <dd>{{ m.member_code }}</dd>
            <dt>Name</dt>
            <dd>{{ m.full_name }}</dd>
            <dt>Mobile</dt>
            <dd>{{ m.mobile }}</dd>
            <dt>Joined</dt>
            <dd>{{ m.joining_date | date: 'd MMM y' }}</dd>
            <dt>Status</dt>
            <dd><app-badge [value]="m.status" /></dd>
          </dl>
          @if (m.trainer; as t) {
            <h3 style="margin-top:1rem">Your trainer</h3>
            <p style="margin:0">
              <strong>{{ t.full_name }}</strong>
              @if (t.specialization) {
                · {{ t.specialization }}
              }
              <br /><a [href]="'tel:' + t.mobile">{{ t.mobile }}</a>
            </p>
          }
          <p class="muted small">To change your name or mobile number, please contact the front desk.</p>
        </section>
        <section class="card">
          <h2>Edit details</h2>
          @if (error()) {
            <div class="alert error">{{ error() }}</div>
          }
          <form class="form" [formGroup]="form" (ngSubmit)="save()">
            @if (can('email')) {
              <div class="field"><label for="pe">Email</label><input id="pe" type="email" formControlName="email" /></div>
            }
            @if (can('gender')) {
              <div class="field">
                <label for="pg">Gender</label>
                <select id="pg" formControlName="gender">
                  <option [ngValue]="null">—</option>
                  <option value="male">Male</option>
                  <option value="female">Female</option>
                  <option value="other">Other</option>
                </select>
              </div>
            }
            @if (can('date_of_birth')) {
              <div class="field"><label for="pdb">Date of birth</label><input id="pdb" type="date" formControlName="date_of_birth" /></div>
            }
            @if (can('address')) {
              <div class="field"><label for="pa">Address</label><textarea id="pa" formControlName="address"></textarea></div>
            }
            <button class="btn primary" type="submit" [disabled]="form.invalid || form.pristine">Save</button>
          </form>
        </section>
      </div>
    }
  `,
})
export class ProfilePage implements OnInit {
  private api = inject(Api);
  private toast = inject(ToastService);
  protected m = signal<Member | null>(null);
  protected editable = signal<string[]>([]);
  protected error = signal('');
  protected form = inject(FormBuilder).group({
    email: ['', Validators.email],
    gender: [null as string | null],
    date_of_birth: [''],
    address: [''],
  });

  ngOnInit() {
    this.api.get<string[]>('/me/profile/editable-fields').subscribe((f) => this.editable.set(f));
    this.api.get<Member>('/me/profile').subscribe((m) => {
      this.m.set(m);
      this.form.patchValue(m as any);
      this.form.markAsPristine();
    });
  }

  onPhoto(updated: Member) {
    this.m.update((m) => (m ? { ...m, photo_url: updated.photo_url } : m));
    this.toast.ok(updated.photo_url ? 'Photo updated' : 'Photo removed');
  }

  can(field: string) {
    return this.editable().includes(field);
  }

  save() {
    const raw = this.form.getRawValue() as Record<string, any>;
    const body = Object.fromEntries(
      this.editable()
        .filter((k) => k in raw)
        .map((k) => [k, raw[k] === '' ? null : raw[k]]),
    );
    this.api.patch<Member>('/me/profile', body).subscribe({
      next: (m) => {
        this.m.set(m);
        this.form.markAsPristine();
        this.error.set('');
        this.toast.ok('Profile updated');
      },
      error: (e) => this.error.set(errorMessage(e)),
    });
  }
}
