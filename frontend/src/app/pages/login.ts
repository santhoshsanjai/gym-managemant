import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { errorMessage } from '../core/api.service';
import { AuthService } from '../core/auth.service';

@Component({
  selector: 'app-login',
  imports: [ReactiveFormsModule],
  template: `
    <div class="auth-wrap">
      <div class="card auth-card">
        <div class="brand"><span class="logo">GM</span> Gym Manager</div>
        <p class="muted" style="text-align:center;margin-top:0">Sign in to continue</p>
        @if (expired) {
          <div class="alert info">Your session ended. Please sign in again.</div>
        }
        @if (error()) {
          <div class="alert error" role="alert">{{ error() }}</div>
        }
        <form class="form" [formGroup]="form" (ngSubmit)="submit()">
          <div class="field">
            <label for="username">Mobile number, email or username</label>
            <input id="username" formControlName="username" autocomplete="username" autocapitalize="off" />
          </div>
          <div class="field">
            <label for="password">Password</label>
            <input id="password" type="password" formControlName="password" autocomplete="current-password" />
          </div>
          <button class="btn primary block" type="submit" [disabled]="form.invalid || busy()">
            {{ busy() ? 'Signing in…' : 'Sign in' }}
          </button>
        </form>
        <p class="muted small" style="text-align:center;margin-bottom:0">Forgot your password? Ask the gym front desk to reset it.</p>
      </div>
    </div>
  `,
})
export class LoginPage {
  private fb = inject(FormBuilder);
  private auth = inject(AuthService);
  private router = inject(Router);
  private route = inject(ActivatedRoute);
  protected busy = signal(false);
  protected error = signal('');
  protected expired = !!this.route.snapshot.queryParamMap.get('expired');
  protected form = this.fb.nonNullable.group({
    username: ['', Validators.required],
    password: ['', Validators.required],
  });

  submit() {
    if (this.form.invalid) return;
    this.busy.set(true);
    this.error.set('');
    const { username, password } = this.form.getRawValue();
    this.auth.login(username, password).subscribe({
      next: async (t) => {
        await this.auth.refreshUser();
        this.busy.set(false);
        if (t.must_change_password) return this.router.navigateByUrl('/change-password');
        const next = this.route.snapshot.queryParamMap.get('next');
        return this.router.navigateByUrl(next && next.startsWith(`/${t.role}`) ? next : this.auth.homeFor(t.role));
      },
      error: (e) => {
        this.busy.set(false);
        this.error.set(errorMessage(e));
      },
    });
  }
}
