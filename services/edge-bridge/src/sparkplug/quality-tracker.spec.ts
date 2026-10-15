import { describe, expect, it } from 'vitest';
import type { MetricDef } from '@vbp/contracts';
import { QUALITY, QualityTracker, metricQuality } from './quality-tracker.js';

describe('QualityTracker', () => {
  it('goes stale on a miss and dead after 3', () => {
    const q = new QualityTracker();
    expect(q.record(true, 1)).toBe('online');
    expect(q.record(false)).toBe('stale');
    expect(q.record(false)).toBe('stale');
    expect(q.record(false)).toBe('dead');
    expect(q.record(true, 2)).toBe('online');
  });

  it('counts a frozen PLC heartbeat as a miss', () => {
    const q = new QualityTracker();
    q.record(true, 7);
    expect(q.record(true, 7)).toBe('stale');
    q.record(true, 7);
    expect(q.record(true, 7)).toBe('dead');
    expect(q.record(true, 8)).toBe('online');
  });
});

describe('metricQuality', () => {
  const temp: MetricDef = {
    name: 'TT202_OutTemp',
    type: 'Double',
    unit: '°C',
    source: { kind: 'status', mw: 61, scale: 10, bool: false },
  };
  const state: MetricDef = {
    name: 'State',
    type: 'Int32',
    source: { kind: 'status', mw: 50, scale: 1, bool: false },
  };

  it('marks measurements bad when the unit has lost comms, but not the PLC state', () => {
    expect(metricQuality(temp, 'online', false)).toBe(QUALITY.bad);
    expect(metricQuality(state, 'online', false)).toBe(QUALITY.good);
    expect(metricQuality(temp, 'online', true)).toBe(QUALITY.good);
  });

  it('marks everything stale while the PLC link is down', () => {
    expect(metricQuality(state, 'stale', true)).toBe(QUALITY.stale);
  });
});
