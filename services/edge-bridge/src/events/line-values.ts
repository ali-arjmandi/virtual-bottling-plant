// One poll's decoded values, by device and metric name.
import type { MetricValue } from '../modbus/value-decoder.js';

export type LineValues = ReadonlyMap<string, ReadonlyMap<string, MetricValue>>;

export function numberAt(values: LineValues, device: string, metric: string): number {
  const v = values.get(device)?.get(metric);
  if (typeof v === 'number') return v;
  if (typeof v === 'boolean') return v ? 1 : 0;
  throw new Error(`${device}/${metric}: no value`);
}

export function boolAt(values: LineValues, device: string, metric: string): boolean {
  return numberAt(values, device, metric) !== 0;
}
