import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from './auth.service';
import { Role } from './models';

function roleGuard(role: Role): CanActivateFn {
  return async (_route, state) => {
    const auth = inject(AuthService);
    const router = inject(Router);
    const user = await auth.ensureUser();
    if (!user) return router.createUrlTree(['/login'], { queryParams: { next: state.url } });
    if (user.must_change_password) return router.createUrlTree(['/change-password']);
    if (user.role !== role) return router.createUrlTree([auth.homeFor(user.role)]);
    return true;
  };
}

export const adminGuard = roleGuard('admin');
export const memberGuard = roleGuard('member');

export const signedInGuard: CanActivateFn = async () => {
  const auth = inject(AuthService);
  const router = inject(Router);
  const user = await auth.ensureUser();
  return user ? true : router.createUrlTree(['/login']);
};

export const landingGuard: CanActivateFn = async () => {
  const auth = inject(AuthService);
  const router = inject(Router);
  const user = await auth.ensureUser();
  return router.createUrlTree([user ? auth.homeFor(user.role) : '/login']);
};
