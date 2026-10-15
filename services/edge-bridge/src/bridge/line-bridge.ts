// One poll cycle of Line 1: read the PLC, publish Sparkplug births/data/deaths with quality,
// detect JSON events, and drive the recipe handshake. Commands come in through the handlers.
import type { Logger } from 'pino';
import { validateMessage, type MetricCatalog, type RecipeCommand } from '@vbp/contracts';
import type { UMetric } from 'sparkplug-payload/lib/sparkplugbpayload.js';
import type { BlockReader } from '../modbus/block-reader.js';
import type { PlcClient } from '../modbus/plc-client.js';
import {
  decodeMetric,
  toSigned16,
  type MetricValue,
  type PlcSnapshot,
} from '../modbus/value-decoder.js';
import type { NodeSession } from '../sparkplug/node-session.js';
import type { MetricPublisher, MetricSample } from '../sparkplug/metric-publisher.js';
import {
  metricQuality,
  type LinkState,
  type QualityTracker,
} from '../sparkplug/quality-tracker.js';
import type { SimTimestamp } from '../time/sim-timestamp.js';
import type { EventPublisher } from '../events/event-publisher.js';
import type { LineValues } from '../events/line-values.js';
import type { StateChangeDetector } from '../events/state-change-detector.js';
import type { ProcessEventDetector } from '../events/process-event-detector.js';
import type { DcmdHandler } from '../commands/dcmd-handler.js';
import {
  resultBody,
  type HandshakeAction,
  type RecipeHandshake,
} from '../commands/recipe-handshake.js';
import { RECIPE_ACK_MW, RECIPE_NAK_MW, type WordWrite } from '../commands/recipe-words.js';

export type LineBridgeDeps = {
  plc: PlcClient;
  reader: BlockReader;
  session: NodeSession;
  catalog: MetricCatalog;
  metrics: MetricPublisher;
  quality: QualityTracker;
  simTime: SimTimestamp;
  events: EventPublisher;
  states: StateChangeDetector;
  process: ProcessEventDetector;
  dcmd: DcmdHandler;
  handshake: RecipeHandshake;
  log: Logger;
  pollMs: number;
};

export class LineBridge {
  private timer: NodeJS.Timeout | null = null;
  private nodeBirthPending = true;
  private devicesBorn = false;
  private link: LinkState = 'dead';
  private values: LineValues = new Map();

  constructor(private readonly d: LineBridgeDeps) {}

  get linkState(): LinkState {
    return this.link;
  }

  start(): void {
    this.d.session.onOnline(() => this.rebirth());
    this.d.session.onCommand((device, metrics) => this.onCommand(device, metrics));
    const loop = async () => {
      const started = Date.now();
      await this.cycle().catch((err) => this.d.log.error({ err }, 'poll cycle failed'));
      this.timer = setTimeout(loop, Math.max(0, this.d.pollMs - (Date.now() - started)));
    };
    void loop();
  }

  stop(): void {
    if (this.timer) clearTimeout(this.timer);
  }

  onRecipe(payload: unknown): void {
    const error = validateMessage('recipe-command', payload);
    if (error) {
      const p = (payload ?? {}) as Partial<RecipeCommand>;
      const ref = {
        messageId: typeof p.messageId === 'string' ? p.messageId : '',
        recipeId: Number.isInteger(p.recipeId) ? p.recipeId! : 0,
        recipeVersion: Number.isInteger(p.recipeVersion) ? p.recipeVersion! : 0,
      };
      this.d.log.warn({ error }, 'recipe command invalid');
      this.d.events.send(
        'recipe_result',
        resultBody(ref, 'Invalid', null, error, 0),
        this.d.simTime.now(),
      );
      return;
    }
    this.d.log.info({ recipe: payload }, 'recipe download requested');
    this.execute(this.d.handshake.request(payload as RecipeCommand, Date.now()));
  }

  private rebirth(): void {
    this.nodeBirthPending = true;
    this.devicesBorn = false;
  }

  private async cycle(): Promise<void> {
    let snapshot: PlcSnapshot | null = null;
    try {
      snapshot = await this.d.reader.read();
    } catch (err) {
      this.d.log.debug({ err: (err as Error).message }, 'PLC poll missed');
    }
    const previous = this.link;
    const decoded = snapshot ? this.decodeAll(snapshot) : null;
    const heartbeat = decoded?.get('LINE')?.get('PlcHeartbeat');
    this.link = this.d.quality.record(
      snapshot !== null,
      typeof heartbeat === 'number' ? heartbeat : undefined,
    );
    if (decoded && this.link === 'online') {
      this.values = decoded;
      const sim = this.d.simTime.update(Number(this.values.get('LINE')?.get('SimTimeMs') ?? 0));
      if (sim.reset) {
        this.d.log.info('sim clock reset: rebirth');
        this.rebirth();
      }
    }
    if (this.link !== previous)
      this.d.log.info({ from: previous, to: this.link }, 'PLC link state');
    this.publishSparkplug(previous);
    if (snapshot && this.link === 'online') {
      this.publishEvents();
      this.execute(
        this.d.handshake.poll(
          {
            ack: (snapshot.mw.get(RECIPE_ACK_MW) ?? 0) !== 0,
            nak: toSigned16(snapshot.mw.get(RECIPE_NAK_MW) ?? 0),
          },
          Date.now(),
        ),
      );
    }
  }

  private publishSparkplug(previous: LinkState): void {
    const { session } = this.d;
    if (!session.connected) return;
    const ts = this.d.simTime.now();
    if (this.nodeBirthPending) {
      session.birthNode(ts);
      this.nodeBirthPending = false;
    }
    if (this.link === 'dead') {
      if (this.devicesBorn)
        for (const device of Object.keys(this.d.catalog)) session.deathDevice(device, ts);
      this.devicesBorn = false;
      return;
    }
    if (this.link === 'stale' && previous === 'stale') return;
    if (!this.devicesBorn) {
      if (this.link !== 'online') return;
      for (const [device, samples] of this.samples()) {
        session.birthDevice(device, samples, ts);
        this.d.metrics.birth(device, samples);
      }
      this.devicesBorn = true;
      this.d.states.reset();
      return;
    }
    for (const [device, samples] of this.samples())
      session.deviceData(device, this.d.metrics.changes(device, samples), ts);
  }

  private publishEvents(): void {
    const ts = this.d.simTime.now();
    for (const { cell, body } of this.d.states.detect(this.values))
      this.d.events.send('state', body, ts, cell);
    const { batch, divert } = this.d.process.detect(this.values);
    for (const body of batch) this.d.events.send('batch', body, ts);
    for (const body of divert) this.d.events.send('divert', body, ts);
  }

  private samples(): [string, MetricSample[]][] {
    return Object.entries(this.d.catalog).map(([device, defs]) => {
      const values = this.values.get(device);
      const commsOk = values?.get('CommsOk') !== false;
      return [
        device,
        defs.map((def) => ({
          def,
          value: values?.get(def.name) ?? false,
          quality: metricQuality(def, this.link, commsOk),
        })),
      ];
    });
  }

  private decodeAll(snapshot: PlcSnapshot): Map<string, Map<string, MetricValue>> {
    return new Map(
      Object.entries(this.d.catalog).map(([device, defs]) => [
        device,
        new Map(defs.map((def) => [def.name, decodeMetric(def, snapshot)])),
      ]),
    );
  }

  private onCommand(device: string | null, metrics: UMetric[]): void {
    const { writes, rebirth } = this.d.dcmd.handle(device, metrics);
    if (rebirth) {
      this.d.log.info('rebirth requested');
      this.rebirth();
    }
    for (const write of writes) this.write(write);
  }

  private execute(actions: HandshakeAction[]): void {
    for (const a of actions) {
      if (a.kind === 'write') this.write(a.write);
      else {
        this.d.log.info({ result: a.body }, 'recipe result');
        this.d.events.send('recipe_result', a.body, this.d.simTime.now());
      }
    }
  }

  private write(w: WordWrite): void {
    this.d.plc
      .writeMw(w.mw, w.values)
      .then(() => this.d.log.debug({ mw: w.mw, values: w.values }, 'PLC write'))
      .catch((err) =>
        this.d.log.error({ mw: w.mw, err: (err as Error).message }, 'PLC write failed'),
      );
  }
}
