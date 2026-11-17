import { Component, computed, input } from '@angular/core';

const TONES: Record<string, string> = {
  active: 'green',
  paid: 'green',
  qr: 'blue',
  upcoming: 'blue',
  manual: 'gray',
  pending: 'amber',
  suspended: 'amber',
  expired: 'red',
  failed: 'red',
  cancelled: 'gray',
  inactive: 'gray',
  refunded: 'gray',
  none: 'gray',
};

@Component({
  selector: 'app-badge',
  template: `<span class="badge" [class]="'badge ' + tone()">{{ label() }}</span>`,
})
export class Badge {
  value = input.required<string | null | undefined>();
  text = input<string>();
  tone = computed(() => TONES[this.value() ?? ''] ?? 'gray');
  label = computed(() => this.text() ?? humanize(this.value() ?? '—'));
}

export function humanize(v: string): string {
  return v.replace(/_/g, ' ').replace(/^\w/, (c) => c.toUpperCase());
}
