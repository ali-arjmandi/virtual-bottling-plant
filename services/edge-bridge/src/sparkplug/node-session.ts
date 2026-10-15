// Sparkplug B edge-node session for DelftsSap/Line1 (contracts.md §3): MQTT connection with the
// NDEATH will, bdSeq per connection, seq 0–255 per message, births, data, deaths and commands.
import mqtt, { type IClientOptions, type MqttClient } from 'mqtt';
import sparkplugPayload from 'sparkplug-payload';
import type { UMetric, UPayload } from 'sparkplug-payload/lib/sparkplugbpayload.js';
import type { Logger } from 'pino';
import { sparkplugTopic, topicsDoc, type SparkplugMessageType } from '@vbp/contracts';
import type { MetricSample } from './metric-publisher.js';

const codec = sparkplugPayload.get('spBv1.0');
if (!codec) throw new Error('sparkplug-payload: spBv1.0 codec missing');
const sparkplug = codec;

export type MqttOptions = { url: string; username: string; password: string; ca?: Buffer };
export type CommandHandler = (device: string | null, metrics: UMetric[]) => void;
export type JsonHandler = (payload: unknown) => void;

export function toSparkplugMetric(s: MetricSample, timestamp: number): UMetric {
  return {
    name: s.def.name,
    type: s.def.type,
    value: s.value,
    timestamp,
    properties: { Quality: { type: 'Int32', value: s.quality } },
  };
}

export class NodeSession {
  private client: MqttClient | null = null;
  private bdSeq = 0;
  private seq = 0;
  private readonly jsonHandlers = new Map<string, JsonHandler>();
  private commandHandler: CommandHandler = () => {};
  private onlineHandler: () => void = () => {};

  constructor(
    private readonly opts: MqttOptions,
    private readonly log: Logger,
  ) {}

  get connected(): boolean {
    return this.client?.connected ?? false;
  }

  onOnline(handler: () => void): void {
    this.onlineHandler = handler;
  }
  onCommand(handler: CommandHandler): void {
    this.commandHandler = handler;
  }
  onJson(topic: string, handler: JsonHandler): void {
    this.jsonHandlers.set(topic, handler);
  }

  start(): void {
    const options: IClientOptions = {
      username: this.opts.username,
      password: this.opts.password,
      ca: this.opts.ca,
      protocolVersion: 5,
      clean: true,
      reconnectPeriod: 2000,
      connectTimeout: 10_000,
      clientId: `edge-bridge-${topicsDoc.sparkplug.node}`,
      will: this.will(),
    };
    const client = mqtt.connect(this.opts.url, options);
    this.client = client;
    client.on('connect', () => {
      this.log.info({ bdSeq: this.bdSeq }, 'MQTT connected');
      client.subscribe(
        [sparkplugTopic('NCMD'), `${sparkplugTopic('DCMD')}/+`, ...this.jsonHandlers.keys()],
        { qos: 1 },
      );
      this.onlineHandler();
    });
    client.on('close', () => {
      // The next connection is a new Sparkplug session: its will carries the next bdSeq.
      this.bdSeq = (this.bdSeq + 1) % 256;
      client.options.will = this.will();
    });
    client.on('error', (err) => this.log.warn({ err: err.message }, 'MQTT error'));
    client.on('message', (topic, payload) => this.dispatch(topic, payload));
  }

  async stop(): Promise<void> {
    if (!this.client) return;
    if (this.client.connected) {
      await this.client.publishAsync(sparkplugTopic('NDEATH'), this.deathPayload(), { qos: 1 });
    }
    await this.client.endAsync();
  }

  birthNode(timestamp: number): void {
    this.seq = 0;
    this.publishSparkplug('NBIRTH', undefined, {
      timestamp,
      seq: this.seq,
      metrics: [
        { name: 'bdSeq', type: 'UInt64', value: this.bdSeq, timestamp },
        { name: 'Node Control/Rebirth', type: 'Boolean', value: false, timestamp },
      ],
    });
  }

  birthDevice(device: string, samples: MetricSample[], timestamp: number): void {
    this.publishDevice('DBIRTH', device, samples, timestamp);
  }

  deviceData(device: string, samples: MetricSample[], timestamp: number): void {
    if (samples.length) this.publishDevice('DDATA', device, samples, timestamp);
  }

  deathDevice(device: string, timestamp: number): void {
    this.publishSparkplug('DDEATH', device, { timestamp, seq: this.nextSeq(), metrics: [] });
  }

  publishJson(topic: string, body: unknown, retain: boolean): void {
    this.client?.publish(topic, JSON.stringify(body), { qos: 1, retain });
  }

  private publishDevice(
    type: SparkplugMessageType,
    device: string,
    samples: MetricSample[],
    ts: number,
  ): void {
    const metrics = samples.map((s) => toSparkplugMetric(s, ts));
    this.publishSparkplug(type, device, { timestamp: ts, seq: this.nextSeq(), metrics });
  }

  private publishSparkplug(
    type: SparkplugMessageType,
    device: string | undefined,
    payload: UPayload,
  ): void {
    if (!this.client?.connected) return;
    this.client.publish(
      sparkplugTopic(type, device),
      Buffer.from(sparkplug.encodePayload(payload)),
      { qos: 0 },
    );
  }

  private nextSeq(): number {
    this.seq = (this.seq + 1) % 256;
    return this.seq;
  }

  private deathPayload(): Buffer {
    return Buffer.from(
      sparkplug.encodePayload({
        timestamp: Date.now(),
        metrics: [{ name: 'bdSeq', type: 'UInt64', value: this.bdSeq }],
      }),
    );
  }

  private will(): IClientOptions['will'] {
    return { topic: sparkplugTopic('NDEATH'), payload: this.deathPayload(), qos: 1, retain: false };
  }

  private dispatch(topic: string, payload: Buffer): void {
    const json = this.jsonHandlers.get(topic);
    if (json) {
      try {
        json(JSON.parse(payload.toString('utf8')));
      } catch (err) {
        this.log.warn({ topic, err: (err as Error).message }, 'JSON message rejected');
      }
      return;
    }
    const parts = topic.split('/');
    const type = parts[2];
    if (type !== 'NCMD' && type !== 'DCMD') return;
    try {
      const metrics = (sparkplug.decodePayload(payload).metrics ?? []) as UMetric[];
      this.commandHandler(type === 'DCMD' ? (parts[4] ?? '') : null, metrics);
    } catch (err) {
      this.log.warn({ topic, err: (err as Error).message }, 'Sparkplug command rejected');
    }
  }
}
