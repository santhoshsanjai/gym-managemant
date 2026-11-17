import { CurrencyPipe, DatePipe } from '@angular/common';
import { Badge } from './badge';
import { Modal } from './modal';
import { Pager } from './pager';
import { DurationPipe, HumanizePipe } from './pipes';

/** Commonly used building blocks; spread into a component's `imports`. */
export const SHARED = [Badge, Modal, Pager, DurationPipe, HumanizePipe, DatePipe, CurrencyPipe] as const;
