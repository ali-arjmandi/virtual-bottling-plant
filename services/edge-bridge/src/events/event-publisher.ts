// JSON events on the ISA-95 topic tree (contracts.md §3): adds the envelope, validates against
// the contract schema and publishes. An invalid event is a bridge bug: logged, never sent.
import { randomUUID } from 'node:crypto';
import type { Logger } from 'pino';
import {
  jsonTopic,
  topicsDoc,
  validateMessage,
  type Envelope,
  type JsonTopicName,
  type SchemaName,
} from '@vbp/contracts';

export type EventBody<T> = Omit<T, keyof Envelope>;
export type JsonPublish = (topic: string, body: unknown, retain: boolean) => void;

export const SCHEMA_VERSION = '1.0';
export const SOURCE = 'edge-bridge';

export function envelope(simTimeMs: number): Envelope {
  return {
    ts: new Date(simTimeMs).toISOString(),
    source: SOURCE,
    schemaVersion: SCHEMA_VERSION,
    messageId: randomUUID(),
  };
}

export class EventPublisher {
  constructor(
    private readonly publish: JsonPublish,
    private readonly log: Logger,
  ) {}

  send(name: JsonTopicName, body: object, simTimeMs: number, cell?: string): void {
    const spec = topicsDoc.json.topics[name];
    if (!spec) throw new Error(`unknown topic ${name}`);
    const message = { ...envelope(simTimeMs), ...body };
    const error = validateMessage(spec.schema as SchemaName, message);
    if (error) {
      this.log.error({ topic: name, error }, 'event does not match its schema, not sent');
      return;
    }
    this.publish(jsonTopic(name, cell), message, spec.retained);
  }
}
