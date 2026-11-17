import { Component, computed, input, output } from '@angular/core';

@Component({
  selector: 'app-pager',
  template: `
    @if (total() > 0) {
      <nav class="pager" aria-label="Pagination">
        <span class="muted">{{ from() }}–{{ to() }} of {{ total() }}</span>
        <span class="spacer"></span>
        <button class="btn sm" type="button" [disabled]="page() <= 1" (click)="pageChange.emit(page() - 1)">Previous</button>
        <button class="btn sm" type="button" [disabled]="page() >= pages()" (click)="pageChange.emit(page() + 1)">Next</button>
      </nav>
    }
  `,
})
export class Pager {
  page = input.required<number>();
  pageSize = input.required<number>();
  total = input.required<number>();
  pageChange = output<number>();
  pages = computed(() => Math.max(1, Math.ceil(this.total() / this.pageSize())));
  from = computed(() => (this.page() - 1) * this.pageSize() + 1);
  to = computed(() => Math.min(this.total(), this.page() * this.pageSize()));
}
