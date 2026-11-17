import { Component, OnDestroy, OnInit, computed, inject, signal } from '@angular/core';
import { NavigationEnd, Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { Subscription, filter } from 'rxjs';
import { Api } from '../core/api.service';
import { AuthService } from '../core/auth.service';

interface NavItem {
  link: string;
  label: string;
  icon: string;
  exact?: boolean;
  mobile?: boolean;
}

const ADMIN_NAV: NavItem[] = [
  { link: '/admin', label: 'Dashboard', icon: '▦', exact: true },
  { link: '/admin/members', label: 'Members', icon: '👥' },
  { link: '/admin/subscriptions', label: 'Subscriptions', icon: '🗓' },
  { link: '/admin/payments', label: 'Payments', icon: '₹' },
  { link: '/admin/attendance', label: 'Attendance', icon: '✓' },
  { link: '/admin/trainers', label: 'Trainers', icon: '🏋' },
  { link: '/admin/packages', label: 'Packages', icon: '📦' },
  { link: '/admin/reports', label: 'Reports', icon: '⤓' },
  { link: '/admin/notifications', label: 'Alerts', icon: '🔔' },
  { link: '/admin/activity', label: 'Activity log', icon: '☰' },
  { link: '/admin/settings', label: 'Settings', icon: '⚙' },
];

const MEMBER_NAV: NavItem[] = [
  { link: '/member', label: 'Home', icon: '⌂', exact: true, mobile: true },
  { link: '/member/scan', label: 'Check in', icon: '⌗', mobile: true },
  { link: '/member/attendance', label: 'History', icon: '✓', mobile: true },
  { link: '/member/subscription', label: 'Subscription', icon: '🗓' },
  { link: '/member/packages', label: 'Packages', icon: '📦' },
  { link: '/member/notifications', label: 'Notifications', icon: '🔔', mobile: true },
  { link: '/member/profile', label: 'Profile', icon: '☺', mobile: true },
];

@Component({
  selector: 'app-shell',
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  template: `
    <div class="shell" [class.nav-open]="navOpen()">
      <aside class="sidebar" aria-label="Main navigation">
        <div class="brand">
          <span class="logo" aria-hidden="true">GM</span>
          <span>Gym Manager</span>
        </div>
        <nav>
          @for (n of nav(); track n.link) {
            <a
              [routerLink]="n.link"
              routerLinkActive="active"
              [routerLinkActiveOptions]="{ exact: !!n.exact }"
              (click)="navOpen.set(false)"
            >
              <span class="nav-icon" aria-hidden="true">{{ n.icon }}</span>{{ n.label }}
              @if (n.link.endsWith('notifications') && unread() > 0) {
                <span class="count">{{ unread() }}</span>
              }
            </a>
          }
          @if (isAdmin()) {
            <a routerLink="/admin/qr-display" target="_blank"><span class="nav-icon" aria-hidden="true">⌗</span>Gym QR display</a>
          }
        </nav>
        <div class="sidebar-foot">
          <div class="who">{{ auth.user()?.full_name || auth.user()?.username }}</div>
          <button class="btn ghost sm" type="button" routerLink="/change-password">Change password</button>
          <button class="btn ghost sm" type="button" (click)="auth.logout()">Sign out</button>
        </div>
      </aside>
      <div class="backdrop" (click)="navOpen.set(false)"></div>
      <div class="main-col">
        <header class="topbar">
          <button class="icon-btn menu-btn" type="button" aria-label="Open menu" (click)="navOpen.set(true)">☰</button>
          <span class="topbar-title">Gym Manager</span>
          <span class="spacer"></span>
          <a class="icon-btn" [routerLink]="isAdmin() ? '/admin/notifications' : '/member/notifications'" aria-label="Notifications">
            🔔
            @if (unread() > 0) {
              <span class="count">{{ unread() }}</span>
            }
          </a>
        </header>
        <main class="content"><router-outlet /></main>
        @if (!isAdmin()) {
          <nav class="bottom-nav" aria-label="Quick navigation">
            @for (n of mobileNav(); track n.link) {
              <a [routerLink]="n.link" routerLinkActive="active" [routerLinkActiveOptions]="{ exact: !!n.exact }">
                <span aria-hidden="true">{{ n.icon }}</span><small>{{ n.label }}</small>
              </a>
            }
          </nav>
        }
      </div>
    </div>
  `,
})
export class Shell implements OnInit, OnDestroy {
  protected auth = inject(AuthService);
  private api = inject(Api);
  private router = inject(Router);
  protected navOpen = signal(false);
  protected unread = signal(0);
  protected isAdmin = computed(() => this.auth.role() === 'admin');
  protected nav = computed(() => (this.isAdmin() ? ADMIN_NAV : MEMBER_NAV));
  protected mobileNav = computed(() => MEMBER_NAV.filter((n) => n.mobile));
  private sub?: Subscription;

  ngOnInit() {
    this.loadUnread();
    // Refresh the unread badge on navigation instead of polling.
    this.sub = this.router.events.pipe(filter((e) => e instanceof NavigationEnd)).subscribe(() => this.loadUnread());
  }

  ngOnDestroy() {
    this.sub?.unsubscribe();
  }

  private loadUnread() {
    this.api.get<{ unread: number }>('/notifications/unread-count').subscribe({
      next: (r) => this.unread.set(r.unread),
      error: () => {},
    });
  }
}
