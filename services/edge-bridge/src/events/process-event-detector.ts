// Batch and divert events from PLC status edges (EDG-04): T-101 BatchActive and P-201
// XV203_Divert. The first poll only records the levels; events come from changes after it.
import type { BatchEvent, DivertEvent } from '@vbp/contracts';
import { boolAt, numberAt, type LineValues } from './line-values.js';
import type { EventBody } from './event-publisher.js';

export type ProcessEvents = { batch: EventBody<BatchEvent>[]; divert: EventBody<DivertEvent>[] };

export class ProcessEventDetector {
  private batchActive: boolean | null = null;
  private diverting: boolean | null = null;

  detect(values: LineValues): ProcessEvents {
    const events: ProcessEvents = { batch: [], divert: [] };
    const batchActive = boolAt(values, 'T101', 'BatchActive');
    if (this.batchActive !== null && batchActive !== this.batchActive) {
      const end = !batchActive;
      events.batch.push({
        event: end ? 'end' : 'start',
        batchNo: numberAt(values, 'T101', 'BatchNo'),
        productCode: numberAt(values, 'T101', 'ProductCode'),
        concentrateLotNo: numberAt(values, 'T101', 'ConcLotNo'),
        brix: end ? numberAt(values, 'T101', 'BatchBrix') : null,
        brixOk: end ? boolAt(values, 'T101', 'BrixOk') : null,
      });
    }
    this.batchActive = batchActive;

    const diverting = boolAt(values, 'P201', 'XV203_Divert');
    if (this.diverting !== null && diverting !== this.diverting) {
      events.divert.push({
        event: diverting ? 'start' : 'end',
        divertCount: numberAt(values, 'P201', 'DivertCount'),
        outTempC: numberAt(values, 'P201', 'TT202_OutTemp'),
        batchNo: numberAt(values, 'T101', 'BatchNo'),
      });
    }
    this.diverting = diverting;
    return events;
  }
}
