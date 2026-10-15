// Sparkplug commands → PLC command words (EDG-10, EDG-13). DCMD writes go to the metric's
// command word; NCMD handles `Node Control/Rebirth`. Anything unknown is rejected and logged.
import type { Logger } from 'pino';
import type { MetricCatalog } from '@vbp/contracts';
import type { UMetric } from 'sparkplug-payload/lib/sparkplugbpayload.js';
import type { WordWrite } from './recipe-words.js';

export type CommandOutcome = { writes: WordWrite[]; rebirth: boolean };

export class DcmdHandler {
  constructor(
    private readonly catalog: MetricCatalog,
    private readonly log: Logger,
  ) {}

  handle(device: string | null, metrics: UMetric[]): CommandOutcome {
    const outcome: CommandOutcome = { writes: [], rebirth: false };
    for (const m of metrics) {
      if (device === null) {
        if (m.name === 'Node Control/Rebirth' && m.value === true) outcome.rebirth = true;
        else this.reject(null, m, 'unknown node command');
        continue;
      }
      const write = this.toWrite(device, m);
      if (write) outcome.writes.push(write);
    }
    return outcome;
  }

  private toWrite(device: string, m: UMetric): WordWrite | null {
    const defs = this.catalog[device];
    if (!defs) return this.reject(device, m, 'unknown device');
    const def = defs.find((d) => d.name === m.name);
    if (!def?.command)
      return this.reject(device, m, def ? 'metric is read-only' : 'unknown metric');
    const { command } = def;
    if (def.type === 'Boolean') {
      if (typeof m.value !== 'boolean') return this.reject(device, m, 'expected a Boolean');
      if (!m.value) return null; // momentary: only the rising write acts
      return { mw: command.mw, values: [command.value ?? 1] };
    }
    const value = Number(m.value);
    if (!Number.isInteger(value)) return this.reject(device, m, 'expected an integer');
    const [min, max] = command.range ?? [-32768, 65535];
    if (value < min! || value > max!)
      return this.reject(device, m, `out of range [${min}, ${max}]`);
    return { mw: command.mw, values: [Math.round(value * command.scale)] };
  }

  private reject(device: string | null, m: UMetric, why: string): null {
    this.log.warn({ device, metric: m.name, value: String(m.value), why }, 'command rejected');
    return null;
  }
}
