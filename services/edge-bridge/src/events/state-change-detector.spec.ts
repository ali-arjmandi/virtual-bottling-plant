import { describe, expect, it } from 'vitest';
import { StateChangeDetector } from './state-change-detector.js';
import { lineValues } from './test-values.js';

const machine = (State: number, extra: Record<string, number | boolean> = {}) => ({
  State,
  StopReason: 0,
  Blocked: false,
  Starved: false,
  ...extra,
});
const line = (states: Partial<Record<string, number>>, firstOut = 0) =>
  lineValues({
    F401: machine(states.F401 ?? 6),
    C501: machine(states.C501 ?? 6, states.C501 === 11 ? { StopReason: 10 } : {}),
    L601: machine(6),
    Q701: machine(6),
    K801: machine(6),
    LINE: { State: states.F401 ?? 6, FirstOutAlarmId: firstOut },
  });

describe('StateChangeDetector', () => {
  it('publishes every state on the first poll, then only changes', () => {
    const d = new StateChangeDetector();
    const first = d.detect(line({}));
    expect(first[0]?.body).toMatchObject({ state: 'Execute', previousState: 'Execute' });
    expect(first.map((e) => e.cell)).toEqual([
      'filler',
      'capper',
      'labeler',
      'checkweigher',
      'casepacker',
      'line',
    ]);
    expect(d.detect(line({}))).toEqual([]);
    const [jam] = d.detect(line({ C501: 11 }, 10));
    expect(jam).toEqual({
      cell: 'capper',
      body: {
        device: 'C501',
        state: 'Held',
        previousState: 'Execute',
        stopReason: 10,
        blocked: false,
        starved: false,
        firstOutAlarmId: 10,
      },
    });
  });

  it('takes the line flags from the filler and republishes after reset', () => {
    const d = new StateChangeDetector();
    d.detect(line({}));
    const events = d.detect(line({ F401: 5 }));
    expect(events.map((e) => [e.cell, e.body.state])).toEqual([
      ['filler', 'Suspended'],
      ['line', 'Suspended'],
    ]);
    d.reset();
    const again = d.detect(line({ F401: 5 }));
    expect(again).toHaveLength(6);
    expect(again[0]?.body).toMatchObject({ state: 'Suspended', previousState: 'Suspended' });
    expect(d.detect(line({ F401: 5 }))).toEqual([]);
  });
});
