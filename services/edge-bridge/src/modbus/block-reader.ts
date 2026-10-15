// Polls the PLC status, alarm, recipe and counter blocks (EDG-01) into one raw snapshot.
import type { PlcClient } from './plc-client.js';
import type { ReadPlan } from './read-plan.js';
import { joinWords, type PlcSnapshot } from './value-decoder.js';

export class BlockReader {
  constructor(
    private readonly plc: PlcClient,
    private readonly plan: ReadPlan,
  ) {}

  async read(): Promise<PlcSnapshot> {
    const mw = new Map<number, number>();
    for (const span of this.plan.mwSpans) {
      const words = await this.plc.readMw(span.start, span.count);
      words.forEach((w, i) => mw.set(span.start + i, w));
    }
    const md = new Map<number, number>();
    if (this.plan.md) {
      const { start, count } = this.plan.md;
      const words = await this.plc.readMdWords(start, count);
      for (let i = 0; i < count; i++)
        md.set(start + i, joinWords(words[2 * i]!, words[2 * i + 1]!));
    }
    return { mw, md };
  }
}
