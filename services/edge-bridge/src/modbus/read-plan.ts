// Which %MW spans and %MD counters one poll reads: every word the catalog and the recipe
// handshake need, merged into as few requests as fit Modbus' 125-register limit.
import { plcIoDoc, type MetricCatalog } from '@vbp/contracts';

export type Span = { start: number; count: number };
export type ReadPlan = { mwSpans: Span[]; md: { start: number; count: number } | null };

const MAX_REGISTERS = 125;
/** Gaps up to this many unused words are read through rather than split into a new request. */
const MAX_GAP = 30;

export function spansFor(
  addresses: Iterable<number>,
  maxCount = MAX_REGISTERS,
  maxGap = MAX_GAP,
): Span[] {
  const sorted = [...new Set(addresses)].sort((a, b) => a - b);
  const spans: Span[] = [];
  for (const a of sorted) {
    const last = spans[spans.length - 1];
    const end = last ? last.start + last.count : 0;
    if (last && a - end <= maxGap && a - last.start < maxCount) last.count = a - last.start + 1;
    else spans.push({ start: a, count: 1 });
  }
  return spans;
}

export function buildReadPlan(catalog: MetricCatalog, plc = plcIoDoc): ReadPlan {
  const mw: number[] = [];
  const md: number[] = [];
  for (const def of Object.values(catalog).flat()) {
    if (def.source.kind === 'status' || def.source.kind === 'alarm') mw.push(def.source.mw);
    if (def.source.kind === 'counter') md.push(def.source.md);
  }
  for (const w of [...plc.recipe.request, ...plc.recipe.response]) mw.push(w.mw);
  const mdSpan = md.length
    ? { start: Math.min(...md), count: Math.max(...md) - Math.min(...md) + 1 }
    : null;
  return { mwSpans: spansFor(mw), md: mdSpan };
}
