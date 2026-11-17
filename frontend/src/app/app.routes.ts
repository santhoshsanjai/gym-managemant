import { Routes } from '@angular/router';
import { adminGuard, landingGuard, memberGuard, signedInGuard } from './core/guards';
import { Shell } from './layout/shell';

export const routes: Routes = [
  { path: '', pathMatch: 'full', canActivate: [landingGuard], children: [] },
  { path: 'login', loadComponent: () => import('./pages/login').then((m) => m.LoginPage), title: 'Sign in' },
  {
    path: 'change-password',
    canActivate: [signedInGuard],
    loadComponent: () => import('./pages/change-password').then((m) => m.ChangePasswordPage),
    title: 'Change password',
  },
  {
    path: 'kiosk',
    loadComponent: () => import('./pages/admin/qr-display').then((m) => m.QrDisplayPage),
    data: { kiosk: true },
    title: 'Gym QR code',
  },
  {
    path: 'admin/qr-display',
    canActivate: [adminGuard],
    loadComponent: () => import('./pages/admin/qr-display').then((m) => m.QrDisplayPage),
    title: 'Gym QR code',
  },
  {
    path: 'admin',
    component: Shell,
    canActivate: [adminGuard],
    children: [
      { path: '', loadComponent: () => import('./pages/admin/dashboard').then((m) => m.AdminDashboardPage), title: 'Dashboard' },
      { path: 'members', loadComponent: () => import('./pages/admin/members').then((m) => m.MembersPage), title: 'Members' },
      { path: 'members/new', loadComponent: () => import('./pages/admin/member-form').then((m) => m.MemberFormPage), title: 'New member' },
      { path: 'members/:id', loadComponent: () => import('./pages/admin/member-detail').then((m) => m.MemberDetailPage), title: 'Member' },
      {
        path: 'members/:id/edit',
        loadComponent: () => import('./pages/admin/member-form').then((m) => m.MemberFormPage),
        title: 'Edit member',
      },
      { path: 'trainers', loadComponent: () => import('./pages/admin/trainers').then((m) => m.TrainersPage), title: 'Trainers' },
      { path: 'packages', loadComponent: () => import('./pages/admin/packages').then((m) => m.PackagesPage), title: 'Packages' },
      {
        path: 'subscriptions',
        loadComponent: () => import('./pages/admin/subscriptions').then((m) => m.SubscriptionsPage),
        title: 'Subscriptions',
      },
      { path: 'attendance', loadComponent: () => import('./pages/admin/attendance').then((m) => m.AttendancePage), title: 'Attendance' },
      { path: 'payments', loadComponent: () => import('./pages/admin/payments').then((m) => m.PaymentsPage), title: 'Payments' },
      { path: 'reports', loadComponent: () => import('./pages/admin/reports').then((m) => m.ReportsPage), title: 'Reports' },
      { path: 'activity', loadComponent: () => import('./pages/admin/activity').then((m) => m.ActivityPage), title: 'Activity log' },
      { path: 'settings', loadComponent: () => import('./pages/admin/settings').then((m) => m.SettingsPage), title: 'Settings' },
      { path: 'notifications', loadComponent: () => import('./pages/notifications').then((m) => m.NotificationsPage), title: 'Alerts' },
    ],
  },
  {
    path: 'member',
    component: Shell,
    canActivate: [memberGuard],
    children: [
      { path: '', loadComponent: () => import('./pages/member/dashboard').then((m) => m.MemberDashboardPage), title: 'Home' },
      { path: 'scan', loadComponent: () => import('./pages/member/scan').then((m) => m.ScanPage), title: 'Check in' },
      {
        path: 'attendance',
        loadComponent: () => import('./pages/member/attendance').then((m) => m.MyAttendancePage),
        title: 'My attendance',
      },
      {
        path: 'subscription',
        loadComponent: () => import('./pages/member/subscription').then((m) => m.MySubscriptionPage),
        title: 'My subscription',
      },
      { path: 'packages', loadComponent: () => import('./pages/member/packages').then((m) => m.PackagesListPage), title: 'Packages' },
      { path: 'profile', loadComponent: () => import('./pages/member/profile').then((m) => m.ProfilePage), title: 'Profile' },
      {
        path: 'notifications',
        loadComponent: () => import('./pages/notifications').then((m) => m.NotificationsPage),
        title: 'Notifications',
      },
    ],
  },
  { path: '**', redirectTo: '' },
];
