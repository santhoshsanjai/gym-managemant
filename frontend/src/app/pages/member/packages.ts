import { Component, OnInit, inject, signal } from '@angular/core';
import { Api } from '../../core/api.service';
import { Package } from '../../core/models';
import { SHARED } from '../../shared';

@Component({
  selector: 'app-packages-list',
  imports: [...SHARED],
  template: `
    <div class="page-head"><h1>Packages</h1></div>
    <div class="grid two">
      @for (p of packages(); track p.id) {
        <div class="card">
          <h2>{{ p.name }}</h2>
          <div style="font-size:1.6rem;font-weight:700">{{ p.price | currency: 'INR' : 'symbol' : '1.0-0' }}</div>
          <div class="muted">{{ p | duration }}</div>
          @if (p.description) {
            <p>{{ p.description }}</p>
          }
        </div>
      } @empty {
        <p class="muted">No packages available right now.</p>
      }
    </div>
    <p class="muted small">To join or switch packages, please visit the front desk. Online purchase isn't available yet.</p>
  `,
})
export class PackagesListPage implements OnInit {
  private api = inject(Api);
  protected packages = signal<Package[]>([]);

  ngOnInit() {
    this.api.get<Package[]>('/packages/available').subscribe((p) => this.packages.set(p));
  }
}
