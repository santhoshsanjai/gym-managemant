import { Component, ElementRef, inject, input, output, signal, viewChild } from '@angular/core';
import { Api } from '../core/api.service';
import { Member, Page } from '../core/models';

/** Type-ahead search over members; scales to any number of members. */
@Component({
  selector: 'app-member-picker',
  host: { class: 'picker', '(focusout)': 'onBlur($event)' },
  template: `
    @if (selected(); as m) {
      <div class="picker-chosen">
        <span
          >{{ m.full_name }} <span class="muted small">· {{ m.member_code }}</span></span
        >
        <button type="button" class="icon-btn" aria-label="Clear member" (click)="clear()">✕</button>
      </div>
    } @else {
      <input
        #box
        [id]="inputId()"
        type="search"
        autocomplete="off"
        [placeholder]="placeholder()"
        (input)="search(box.value)"
        (keydown.escape)="results.set([])"
        role="combobox"
        [attr.aria-expanded]="results().length > 0"
      />
      @if (results().length) {
        <ul class="picker-list" role="listbox">
          @for (m of results(); track m.id) {
            <li role="option" tabindex="0" (click)="choose(m)" (keydown.enter)="choose(m)">
              <strong>{{ m.full_name }}</strong> <span class="muted small">{{ m.mobile }} · {{ m.member_code }}</span>
            </li>
          }
        </ul>
      }
    }
  `,
})
export class MemberPicker {
  inputId = input('member-picker');
  placeholder = input('Search name, mobile or member ID');
  activeOnly = input(false);
  picked = output<Member | null>();

  private api = inject(Api);
  private host = inject(ElementRef<HTMLElement>);
  protected box = viewChild<ElementRef<HTMLInputElement>>('box');
  protected results = signal<Member[]>([]);
  protected selected = signal<Member | null>(null);
  private timer?: ReturnType<typeof setTimeout>;

  search(q: string) {
    clearTimeout(this.timer);
    if (q.trim().length < 2) return this.results.set([]);
    this.timer = setTimeout(() => {
      this.api
        .get<Page<Member>>('/members', { q, page_size: 8, status: this.activeOnly() ? 'active' : '' })
        .subscribe((p) => this.results.set(p.items));
    }, 250);
  }

  choose(m: Member) {
    this.selected.set(m);
    this.results.set([]);
    this.picked.emit(m);
  }

  clear() {
    this.selected.set(null);
    this.picked.emit(null);
  }

  onBlur(ev: FocusEvent) {
    if (!this.host.nativeElement.contains(ev.relatedTarget as Node)) setTimeout(() => this.results.set([]), 150);
  }
}
