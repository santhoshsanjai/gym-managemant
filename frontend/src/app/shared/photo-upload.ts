import { Component, inject, input, output, signal } from '@angular/core';
import { Api, errorMessage } from '../core/api.service';
import { Member } from '../core/models';
import { Avatar } from './avatar';

const MAX_BYTES = 2 * 1024 * 1024;

/** Shows the current photo with change/remove controls. */
@Component({
  selector: 'app-photo-upload',
  imports: [Avatar],
  template: `
    <div class="photo-upload">
      <app-avatar [name]="name()" [src]="url()" [size]="88" />
      <div>
        <label class="btn sm" [class.disabled]="busy()">
          {{ url() ? 'Change photo' : 'Upload photo' }}
          <input type="file" accept="image/jpeg,image/png,image/webp" capture="user" hidden (change)="pick($event)" [disabled]="busy()" />
        </label>
        @if (url() && removePath()) {
          <button class="btn sm ghost" type="button" (click)="remove()" [disabled]="busy()">Remove</button>
        }
        <div class="hint muted small">JPEG, PNG or WebP, up to 2 MB.</div>
        @if (error()) {
          <div class="err small" role="alert">{{ error() }}</div>
        }
      </div>
    </div>
  `,
})
export class PhotoUpload {
  name = input.required<string>();
  url = input<string | null>(null);
  uploadPath = input.required<string>();
  removePath = input<string | null>(null);
  changed = output<Member>();

  private api = inject(Api);
  protected busy = signal(false);
  protected error = signal('');

  pick(ev: Event) {
    const el = ev.target as HTMLInputElement;
    const file = el.files?.[0];
    el.value = '';
    if (!file) return;
    if (file.size > MAX_BYTES) return this.error.set('That photo is larger than 2 MB.');
    this.run(this.api.upload<Member>(this.uploadPath(), file));
  }

  remove() {
    const p = this.removePath();
    if (p) this.run(this.api.delete<Member>(p));
  }

  private run(obs: ReturnType<Api['upload']>) {
    this.busy.set(true);
    this.error.set('');
    obs.subscribe({
      next: (m) => {
        this.busy.set(false);
        this.changed.emit(m as Member);
      },
      error: (e) => {
        this.busy.set(false);
        this.error.set(errorMessage(e));
      },
    });
  }
}
