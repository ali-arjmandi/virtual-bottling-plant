// UNS timestamps come from the PLC's sim clock (EDG-06), so history lines up under time
// acceleration. SimTimeMs is ms since sim t = 0, mod 2^32; SIM_EPOCH is the wall time of t = 0.
const WRAP = 2 ** 32;

export type SimTimeUpdate = { epochMs: number; reset: boolean };

export class SimTimestamp {
  private lastRaw: number | null = null;
  private wraps = 0;

  constructor(private readonly epochMs: number) {}

  /** Feeds one poll's SimTimeMs. `reset` is true when the sim clock jumped back (`POST /reset`). */
  update(raw: number): SimTimeUpdate {
    let reset = false;
    if (this.lastRaw !== null && raw < this.lastRaw) {
      if (this.lastRaw - raw > WRAP / 2) this.wraps++;
      else {
        this.wraps = 0;
        reset = true;
      }
    }
    this.lastRaw = raw;
    return { epochMs: this.epochMs + this.wraps * WRAP + raw, reset };
  }

  /** Last known sim time as epoch ms, or the epoch before the first poll. */
  now(): number {
    return this.epochMs + this.wraps * WRAP + (this.lastRaw ?? 0);
  }
}
