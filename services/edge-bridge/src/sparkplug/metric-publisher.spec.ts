import { describe, expect, it } from 'vitest';
import type { MetricDef } from '@vbp/contracts';
import { MetricPublisher, type MetricSample } from './metric-publisher.js';
import { QUALITY, type Quality } from './quality-tracker.js';

const temp: MetricDef = {
  name: 'TT202_OutTemp',
  type: 'Double',
  deadband: 0.1,
  source: { kind: 'status', mw: 61, scale: 10, bool: false },
};
const state: MetricDef = {
  name: 'State',
  type: 'Int32',
  source: { kind: 'status', mw: 50, scale: 1, bool: false },
};
const s = (def: MetricDef, value: number, quality: Quality = QUALITY.good): MetricSample => ({
  def,
  value,
  quality,
});
const names = (out: MetricSample[]) => out.map((m) => m.def.name);

describe('MetricPublisher (report by exception)', () => {
  it('sends only changes beyond the deadband, against the last sent value', () => {
    const p = new MetricPublisher();
    p.birth('P201', [s(temp, 85.0), s(state, 6)]);
    expect(names(p.changes('P201', [s(temp, 85.05), s(state, 6)]))).toEqual([]);
    expect(names(p.changes('P201', [s(temp, 85.1), s(state, 6)]))).toEqual(['TT202_OutTemp']);
    // Creeping by 0.05 twice adds up against the last *sent* value.
    expect(names(p.changes('P201', [s(temp, 85.15), s(state, 6)]))).toEqual([]);
    expect(names(p.changes('P201', [s(temp, 85.2), s(state, 6)]))).toEqual(['TT202_OutTemp']);
  });

  it('sends any change without a deadband, and quality changes', () => {
    const p = new MetricPublisher();
    p.birth('C501', [s(state, 6)]);
    expect(names(p.changes('C501', [s(state, 11)]))).toEqual(['State']);
    expect(names(p.changes('C501', [s(state, 11, QUALITY.stale)]))).toEqual(['State']);
  });

  it('refuses data before birth', () => {
    expect(() => new MetricPublisher().changes('X', [])).toThrow(/before DBIRTH/);
  });
});
