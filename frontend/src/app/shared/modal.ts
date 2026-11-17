import { Component, ElementRef, effect, input, output, viewChild } from '@angular/core';

/** Accessible dialog based on the native <dialog> element. */
@Component({
  selector: 'app-modal',
  template: `
    <dialog #dlg class="modal" (close)="closed.emit()" (cancel)="closed.emit()" [attr.aria-label]="title()">
      <header class="modal-head">
        <h2>{{ title() }}</h2>
        <button type="button" class="icon-btn" aria-label="Close" (click)="closed.emit()">✕</button>
      </header>
      <div class="modal-body"><ng-content /></div>
    </dialog>
  `,
})
export class Modal {
  title = input.required<string>();
  open = input<boolean>(false);
  closed = output<void>();
  private dlg = viewChild.required<ElementRef<HTMLDialogElement>>('dlg');

  constructor() {
    effect(() => {
      const d = this.dlg().nativeElement;
      if (this.open() && !d.open) d.showModal();
      if (!this.open() && d.open) d.close();
    });
  }
}
