import { describe, expect, it } from 'vitest';
import { buildMetricCatalog } from '@vbp/contracts';
import { buildReadPlan, spansFor } from './read-plan.js';

describe('read plan', () => {
  it('merges close addresses and splits at the 125-register limit', () => {
    expect(spansFor([0, 1, 2, 10])).toEqual([{ start: 0, count: 11 }]);
    expect(spansFor([0, 100])).toEqual([
      { start: 0, count: 1 },
      { start: 100, count: 1 },
    ]);
    expect(spansFor([0, 20, 40, 60, 80, 100, 120, 130])).toEqual([
      { start: 0, count: 121 },
      { start: 130, count: 1 },
    ]);
  });

  it('covers every catalog word within Modbus limits', () => {
    const catalog = buildMetricCatalog();
    const plan = buildReadPlan(catalog);
    const covered = (mw: number) =>
      plan.mwSpans.some((s) => mw >= s.start && mw < s.start + s.count);
    for (const def of Object.values(catalog).flat()) {
      if (def.source.kind === 'status' || def.source.kind === 'alarm')
        expect(covered(def.source.mw)).toBe(true);
    }
    expect([900, 901, 902, 911].every(covered)).toBe(true);
    expect(plan.mwSpans.every((s) => s.count <= 125)).toBe(true);
    expect(plan.md).toEqual({ start: 0, count: 9 });
  });
});
