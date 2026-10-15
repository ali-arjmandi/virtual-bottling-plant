// Data quality per device (EDG-05). A failed poll makes every value stale; after 3 misses in a
// row the devices are declared dead (DDEATH) and re-birthed when polls succeed again. A PLC
// that answers but stopped scanning (frozen PlcHeartbeat) counts as a miss. A device whose
// remote I/O is lost (CommsOk = false) keeps publishing, with its measurements marked bad.
import type { MetricDef } from '@vbp/contracts';

/** Sparkplug `Quality` property values as Ignition reads them. */
export const QUALITY = { good: 192, bad: 0, stale: 500 } as const;
export type Quality = (typeof QUALITY)[keyof typeof QUALITY];

export type LinkState = 'online' | 'stale' | 'dead';

const DEAD_AFTER_MISSES = 3;

export class QualityTracker {
  private misses = 0;
  private lastHeartbeat: number | null = null;

  /** Records one poll. Returns the link state after it. */
  record(ok: boolean, plcHeartbeat?: number): LinkState {
    const frozen = ok && plcHeartbeat !== undefined && plcHeartbeat === this.lastHeartbeat;
    if (ok && plcHeartbeat !== undefined) this.lastHeartbeat = plcHeartbeat;
    this.misses = ok && !frozen ? 0 : this.misses + 1;
    return this.state;
  }

  get state(): LinkState {
    if (this.misses === 0) return 'online';
    return this.misses >= DEAD_AFTER_MISSES ? 'dead' : 'stale';
  }
}

/** Measured values (they have a unit, or are nozzle stats or counters) go bad on comms loss. */
export function isMeasurement(def: MetricDef): boolean {
  return def.unit !== undefined || def.name.startsWith('Nozzles/') || def.source.kind === 'counter';
}

export function metricQuality(def: MetricDef, link: LinkState, commsOk: boolean): Quality {
  if (link !== 'online') return QUALITY.stale;
  return !commsOk && isMeasurement(def) ? QUALITY.bad : QUALITY.good;
}
