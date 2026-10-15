// PackML state changes of the packaging machines and the line (EDG-03). The first poll after
// start, and the first after a rebirth, publish every current state, so the retained topics are
// filled even after a broker restart. A republished state has previousState = state.
import { plcIoDoc, topicsDoc, type StateEvent } from '@vbp/contracts';
import { boolAt, numberAt, type LineValues } from './line-values.js';
import type { EventBody } from './event-publisher.js';

type PackMLState = StateEvent['state'];

/** Line state = F-401 state (ADR 0003), so the line's stop reason and flags are F-401's. */
const LINE_SOURCE = 'F401';

export class StateChangeDetector {
  private readonly last = new Map<string, number>();
  private republish = false;
  private readonly devices = Object.entries(topicsDoc.sparkplug.devices)
    .filter(([, d]) => d.state_events)
    .map(([id, d]) => ({ id, cell: d.cell }));

  /** Returns one event per device whose State changed since the last poll. */
  detect(values: LineValues): { cell: string; body: EventBody<StateEvent> }[] {
    const out: { cell: string; body: EventBody<StateEvent> }[] = [];
    for (const { id, cell } of this.devices) {
      const state = numberAt(values, id, 'State');
      const previous = this.last.get(id);
      this.last.set(id, state);
      if (previous === state && !this.republish) continue;
      const flags = id === 'LINE' ? LINE_SOURCE : id;
      out.push({
        cell,
        body: {
          device: id,
          state: stateName(state),
          previousState: stateName(previous ?? state),
          stopReason: numberAt(values, flags, 'StopReason'),
          blocked: boolAt(values, flags, 'Blocked'),
          starved: boolAt(values, flags, 'Starved'),
          firstOutAlarmId: numberAt(values, 'LINE', 'FirstOutAlarmId'),
        },
      });
    }
    this.republish = false;
    return out;
  }

  /** The next poll republishes every state (after a rebirth or reconnect). */
  reset(): void {
    this.republish = true;
  }
}

function stateName(code: number): PackMLState {
  return (plcIoDoc.enums.PackMLState?.[String(code)] ?? 'Undefined') as PackMLState;
}
