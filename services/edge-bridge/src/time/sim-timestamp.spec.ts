import { describe, expect, it } from 'vitest';
import { SimTimestamp } from './sim-timestamp.js';

const EPOCH = Date.parse('2026-10-05T05:30:00Z');

describe('SimTimestamp', () => {
  it('adds sim time to the epoch', () => {
    const t = new SimTimestamp(EPOCH);
    expect(t.update(60_000)).toEqual({ epochMs: EPOCH + 60_000, reset: false });
    expect(t.now()).toBe(EPOCH + 60_000);
  });

  it('unwraps the 2^32 ms rollover', () => {
    const t = new SimTimestamp(EPOCH);
    t.update(2 ** 32 - 100);
    expect(t.update(50)).toEqual({ epochMs: EPOCH + 2 ** 32 + 50, reset: false });
  });

  it('reports a sim reset when time jumps back', () => {
    const t = new SimTimestamp(EPOCH);
    t.update(3_600_000);
    expect(t.update(200)).toEqual({ epochMs: EPOCH + 200, reset: true });
  });
});
