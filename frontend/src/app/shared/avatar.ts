import { Component, computed, input } from '@angular/core';

/** Member photo, falling back to initials. */
@Component({
  selector: 'app-avatar',
  template: `
    @if (src()) {
      <img class="avatar" [src]="src()" [alt]="name() + ' photo'" [style.width.px]="size()" [style.height.px]="size()" loading="lazy" />
    } @else {
      <span
        class="avatar initials"
        [style.width.px]="size()"
        [style.height.px]="size()"
        [style.font-size.px]="size() * 0.4"
        aria-hidden="true"
        >{{ initials() }}</span
      >
    }
  `,
})
export class Avatar {
  name = input.required<string>();
  src = input<string | null | undefined>(null);
  size = input(40);
  initials = computed(() =>
    this.name()
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((w) => w[0].toUpperCase())
      .join(''),
  );
}
