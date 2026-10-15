// Report by exception (EDG-02): a metric goes into DDATA when its value moves by at least its
// deadband (any change if it has none) or its quality changes.
import type { MetricDef } from '@vbp/contracts';
import type { MetricValue } from '../modbus/value-decoder.js';
import type { Quality } from './quality-tracker.js';

export type MetricSample = { def: MetricDef; value: MetricValue; quality: Quality };

export class MetricPublisher {
  private readonly last = new Map<string, Map<string, { value: MetricValue; quality: Quality }>>();

  /** Remembers a full set (DBIRTH) as the new reference for this device. */
  birth(device: string, samples: MetricSample[]): void {
    this.last.set(
      device,
      new Map(samples.map((s) => [s.def.name, { value: s.value, quality: s.quality }])),
    );
  }

  /** Samples to send in DDATA, and updates the reference to what was sent. */
  changes(device: string, samples: MetricSample[]): MetricSample[] {
    const ref = this.last.get(device);
    if (!ref) throw new Error(`${device}: DDATA before DBIRTH`);
    const out = samples.filter((s) => {
      const prev = ref.get(s.def.name);
      return !prev || prev.quality !== s.quality || exceeds(prev.value, s.value, s.def.deadband);
    });
    for (const s of out) ref.set(s.def.name, { value: s.value, quality: s.quality });
    return out;
  }

  forget(device: string): void {
    this.last.delete(device);
  }
}

/** Scaled values are float divisions (852 / 10), so 85.1 − 85.0 is 0.0999…: allow for that. */
const FLOAT_TOLERANCE = 1e-9;

function exceeds(prev: MetricValue, next: MetricValue, deadband: number | undefined): boolean {
  if (typeof prev !== 'number' || typeof next !== 'number' || deadband === undefined)
    return prev !== next;
  return Math.abs(next - prev) >= deadband - FLOAT_TOLERANCE;
}
