import { Pipe, PipeTransform } from '@angular/core';
import { humanize } from './badge';

@Pipe({ name: 'duration' })
export class DurationPipe implements PipeTransform {
  transform(p: { duration_value: number; duration_unit: string } | null | undefined): string {
    if (!p) return '';
    const unit = p.duration_value === 1 ? p.duration_unit.replace(/s$/, '') : p.duration_unit;
    return `${p.duration_value} ${unit}`;
  }
}

@Pipe({ name: 'humanize' })
export class HumanizePipe implements PipeTransform {
  transform(v: string | null | undefined): string {
    return v ? humanize(v) : '—';
  }
}
