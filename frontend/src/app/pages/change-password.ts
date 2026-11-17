import { Component, inject, signal } from '@angular/core';
import { AbstractControl, FormBuilder, ReactiveFormsModule, ValidationErrors, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { Api, errorMessage } from '../core/api.service';
import { AuthService } from '../core/auth.service';
import { TokenResponse } from '../core/models';
import { ToastService } from '../core/toast.service';

function matching(group: AbstractControl): ValidationErrors | null {
  return group.get('new_password')?.value === group.get('confirm')?.value ? null : { mismatch: true };
}

@Component({
  selector: 'app-change-password',
  imports: [ReactiveFormsModule],
  template: `
    <div class="auth-wrap">
      <div class="card auth-card">
        <h1 style="margin-bottom:.5rem">Change password</h1>
        @if (auth.user()?.must_change_password) {
          <div class="alert warn">Please choose a new password before continuing.</div>
        }
        @if (error()) {
          <div class="alert error" role="alert">{{ error() }}</div>
        }
        <form class="form" [formGroup]="form" (ngSubmit)="submit()">
          <div class="field">
            <label for="cur">Current password</label>
            <input id="cur" type="password" formControlName="current_password" autocomplete="current-password" />
          </div>
          <div class="field">
            <label for="new">New password</label>
            <input id="new" type="password" formControlName="new_password" autocomplete="new-password" />
            <span class="hint">At least 8 characters.</span>
          </div>
          <div class="field">
            <label for="confirm">Confirm new password</label>
            <input id="confirm" type="password" formControlName="confirm" autocomplete="new-password" />
            @if (form.hasError('mismatch') && form.get('confirm')?.touched) {
              <span class="err">Passwords don't match.</span>
            }
          </div>
          <button class="btn primary block" type="submit" [disabled]="form.invalid || busy()">Save password</button>
          @if (!auth.user()?.must_change_password) {
            <button class="btn ghost block" type="button" (click)="back()">Cancel</button>
          }
        </form>
      </div>
    </div>
  `,
})
export class ChangePasswordPage {
  protected auth = inject(AuthService);
  private api = inject(Api);
  private router = inject(Router);
  private toast = inject(ToastService);
  protected busy = signal(false);
  protected error = signal('');
  protected form = inject(FormBuilder).nonNullable.group(
    {
      current_password: ['', Validators.required],
      new_password: ['', [Validators.required, Validators.minLength(8)]],
      confirm: ['', Validators.required],
    },
    { validators: matching },
  );

  submit() {
    const { current_password, new_password } = this.form.getRawValue();
    this.busy.set(true);
    this.api.post<TokenResponse>('/auth/change-password', { current_password, new_password }).subscribe({
      next: async (t) => {
        this.auth.setToken(t.access_token);
        const u = await this.auth.refreshUser();
        this.toast.ok('Password changed');
        this.router.navigateByUrl(this.auth.homeFor(u?.role));
      },
      error: (e) => {
        this.busy.set(false);
        this.error.set(errorMessage(e));
      },
    });
  }

  back() {
    this.router.navigateByUrl(this.auth.homeFor(this.auth.role()));
  }
}
