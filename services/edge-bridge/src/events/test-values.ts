// Builds LineValues for the event specs: every device gets the given metrics.
import type { MetricValue } from '../modbus/value-decoder.js';
import type { LineValues } from './line-values.js';

export function lineValues(byDevice: Record<string, Record<string, MetricValue>>): LineValues {
  return new Map(Object.entries(byDevice).map(([d, m]) => [d, new Map(Object.entries(m))]));
}
