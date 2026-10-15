// Raw PLC words → engineering values (contracts.md §1–2): signed 16-bit scaled integers, bools,
// enum numbers, alarm-table bits and 32-bit counters (high word first).
import type { MetricDef } from '@vbp/contracts';

export type MetricValue = number | boolean;

/** One poll's raw image: %MW words (unsigned 16-bit) and %MD counters (unsigned 32-bit). */
export type PlcSnapshot = { mw: ReadonlyMap<number, number>; md: ReadonlyMap<number, number> };

export function toSigned16(raw: number): number {
  return raw >= 0x8000 ? raw - 0x10000 : raw;
}

export function joinWords(hi: number, lo: number): number {
  return (hi & 0xffff) * 0x10000 + (lo & 0xffff);
}

const ALARM_BITS = { Active: 0, Acked: 1, FirstOut: 2 } as const;

function word(snapshot: PlcSnapshot, mw: number): number {
  const raw = snapshot.mw.get(mw);
  if (raw === undefined) throw new Error(`%MW${mw} not in the poll snapshot`);
  return raw;
}

export function decodeMetric(def: MetricDef, snapshot: PlcSnapshot): MetricValue {
  const src = def.source;
  switch (src.kind) {
    case 'status': {
      const value = toSigned16(word(snapshot, src.mw));
      if (src.bool) return value !== 0;
      return src.scale === 1 ? value : value / src.scale;
    }
    case 'alarm': {
      const raw = word(snapshot, src.mw);
      return src.field === 'Priority'
        ? (raw >> 8) & 0xf
        : ((raw >> ALARM_BITS[src.field]) & 1) === 1;
    }
    case 'counter': {
      const value = snapshot.md.get(src.md);
      if (value === undefined) throw new Error(`%MD${src.md} not in the poll snapshot`);
      return value;
    }
    case 'momentary':
      return def.type === 'Boolean' ? false : 0;
  }
}
