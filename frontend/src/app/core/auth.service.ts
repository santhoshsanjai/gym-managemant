import { Injectable, computed, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { Observable, firstValueFrom, tap } from 'rxjs';
import { Api } from './api.service';
import { CurrentUser, TokenResponse } from './models';

const TOKEN_KEY = 'gym.token';

function readToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  private api = inject(Api);
  private router = inject(Router);

  readonly token = signal<string | null>(readToken());
  readonly user = signal<CurrentUser | null>(null);
  readonly isLoggedIn = computed(() => !!this.token());
  readonly role = computed(() => this.user()?.role ?? null);

  login(username: string, password: string): Observable<TokenResponse> {
    return this.api.post<TokenResponse>('/auth/login', { username, password }).pipe(tap((t) => this.setToken(t.access_token)));
  }

  setToken(token: string | null) {
    this.token.set(token);
    try {
      if (token) localStorage.setItem(TOKEN_KEY, token);
      else localStorage.removeItem(TOKEN_KEY);
    } catch {
      /* storage unavailable: token lives in memory only */
    }
  }

  /** Loads the current user if a token exists. Returns null when signed out. */
  async ensureUser(): Promise<CurrentUser | null> {
    if (!this.token()) return null;
    if (this.user()) return this.user();
    try {
      const u = await firstValueFrom(this.api.get<CurrentUser>('/auth/me'));
      this.user.set(u);
      return u;
    } catch {
      this.clear();
      return null;
    }
  }

  refreshUser() {
    this.user.set(null);
    return this.ensureUser();
  }

  clear() {
    this.setToken(null);
    this.user.set(null);
  }

  logout() {
    this.clear();
    this.router.navigateByUrl('/login');
  }

  homeFor(role: string | null | undefined) {
    return role === 'admin' ? '/admin' : '/member';
  }
}
