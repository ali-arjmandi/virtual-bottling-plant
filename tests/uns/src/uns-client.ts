// An MQTT client of the UNS as Ignition or MES sees it: tracks the latest Sparkplug metric values
// and every message, and can wait for a condition.
import { readFileSync } from 'node:fs';
import { randomUUID } from 'node:crypto';
import mqtt, { type MqttClient } from 'mqtt';
import sparkplugPayload from 'sparkplug-payload';
import type { UMetric, UPayload } from 'sparkplug-payload/lib/sparkplugbpayload.js';
import { sparkplugTopic } from '@vbp/contracts';
import { testEnv } from './test-env.js';

const codec = sparkplugPayload.get('spBv1.0')!;

export type Received = {
  topic: string;
  at: number;
  json?: Record<string, unknown>;
  sparkplug?: UPayload;
};
type User = 'ignition' | 'mes-api' | 'edge-bridge';

export async function connect(user: User, password = testEnv.password(user)): Promise<MqttClient> {
  return mqtt.connectAsync(testEnv.brokerUrl, {
    username: user,
    password,
    ca: readFileSync(testEnv.caFile),
    protocolVersion: 5,
    reconnectPeriod: 0,
    clientId: `uns-test-${user}-${randomUUID().slice(0, 8)}`,
  });
}

export class UnsClient {
  readonly messages: Received[] = [];
  readonly metrics = new Map<string, Map<string, UMetric>>();

  private constructor(readonly mqtt: MqttClient) {
    mqtt.on('message', (topic, payload) => this.receive(topic, payload));
  }

  static async open(user: User = 'ignition'): Promise<UnsClient> {
    const client = new UnsClient(await connect(user));
    await client.mqtt.subscribeAsync(['spBv1.0/#', 'delftssap/#'], { qos: 1 });
    return client;
  }

  value(device: string, metric: string): UMetric['value'] | undefined {
    return this.metrics.get(device)?.get(metric)?.value;
  }

  since(at: number, filter: (m: Received) => boolean): Received[] {
    return this.messages.filter((m) => m.at >= at && filter(m));
  }

  async waitFor<T>(
    what: string,
    check: () => T | undefined | false,
    timeoutMs = 10_000,
  ): Promise<T> {
    const deadline = Date.now() + timeoutMs;
    for (;;) {
      const result = check();
      if (result) return result;
      if (Date.now() > deadline)
        throw new Error(`timed out after ${timeoutMs} ms waiting for ${what}`);
      await new Promise((r) => setTimeout(r, 50));
    }
  }

  async rebirth(): Promise<void> {
    await this.mqtt.publishAsync(
      sparkplugTopic('NCMD'),
      Buffer.from(
        codec.encodePayload({
          timestamp: Date.now(),
          metrics: [{ name: 'Node Control/Rebirth', type: 'Boolean', value: true }],
        }),
      ),
      { qos: 0 },
    );
  }

  async command(device: string, name: string, value: boolean | number): Promise<void> {
    const type = typeof value === 'boolean' ? 'Boolean' : 'Int32';
    await this.mqtt.publishAsync(
      sparkplugTopic('DCMD', device),
      Buffer.from(
        codec.encodePayload({
          timestamp: Date.now(),
          metrics: [{ name, type, value }],
        }),
      ),
      { qos: 0 },
    );
  }

  close(): Promise<void> {
    return this.mqtt.endAsync();
  }

  private receive(topic: string, payload: Buffer): void {
    const message: Received = { topic, at: Date.now() };
    if (topic.startsWith('spBv1.0/')) {
      const parts = topic.split('/');
      if (parts[1] === 'STATE') return;
      message.sparkplug = codec.decodePayload(payload);
      const device = parts[4];
      if (device && (parts[2] === 'DBIRTH' || parts[2] === 'DDATA')) {
        const values = this.metrics.get(device) ?? new Map<string, UMetric>();
        for (const m of (message.sparkplug.metrics ?? []) as UMetric[]) values.set(m.name ?? '', m);
        this.metrics.set(device, values);
      }
    } else {
      message.json = JSON.parse(payload.toString('utf8'));
    }
    this.messages.push(message);
  }
}
