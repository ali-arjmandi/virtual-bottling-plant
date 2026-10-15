// Shapes of contracts/modbus/plc-io.yaml and contracts/uns/topics.yaml, as the generated
// constants are read. Field meanings: the comments in those YAML files.
import { plcIo } from './generated/plc-io.js';
import { topics } from './generated/topics.js';

export type PlcIoMetric = {
  readonly name: string;
  readonly offset: number;
  readonly enum?: string;
  readonly type?: 'bool';
  readonly scale?: number;
  readonly unit?: string;
  readonly deadband?: number;
  readonly description?: string;
};

export type PlcIoStatusBlock = {
  readonly base: number;
  readonly header?: string;
  readonly metrics: readonly PlcIoMetric[];
  readonly nozzle_subgroups?: {
    readonly first_offset: number;
    readonly count: number;
    readonly fields: readonly string[];
    readonly scale: readonly number[];
  };
};

export type PlcIoAlarm = {
  readonly id: number;
  readonly device: string;
  readonly local: number;
  readonly priority: number;
  readonly name: string;
  readonly text: string;
};

export type PlcIoWord = {
  readonly name: string;
  readonly mw: number;
  readonly enum?: string;
  readonly type?: 'bool';
  readonly scale?: number;
  readonly range?: readonly number[];
};

export type PlcIoDoc = {
  readonly addressing: { readonly mw_holding_base: number; readonly md_holding_base: number };
  readonly enums: Readonly<Record<string, Readonly<Record<string, string>>>>;
  readonly packaging_header: readonly PlcIoMetric[];
  readonly status: Readonly<Record<string, PlcIoStatusBlock>>;
  readonly alarm_table: { readonly base: number; readonly alarms: readonly PlcIoAlarm[] };
  readonly commands: readonly PlcIoWord[];
  readonly recipe: {
    readonly request: readonly PlcIoWord[];
    readonly response: readonly PlcIoWord[];
    readonly timeout_s: number;
  };
  readonly counters: readonly { readonly name: string; readonly md: number }[];
};

export type CommandSpec = {
  readonly metric: string;
  readonly type: 'Boolean' | 'Int32';
  readonly word: string;
  readonly value?: string;
  readonly range?: readonly number[];
};

export type DeviceSpec = {
  readonly area: 'process' | 'packaging';
  readonly cell: string;
  readonly commands?: string;
  readonly state_events?: boolean;
};

export type JsonTopicSpec = {
  readonly path: string;
  readonly publisher: string;
  readonly retained: boolean;
  readonly schema: string;
};

export type TopicsDoc = {
  readonly sparkplug: {
    readonly namespace: string;
    readonly group: string;
    readonly node: string;
    readonly devices: Readonly<Record<string, DeviceSpec>>;
    readonly counter_overrides: Readonly<Record<string, { readonly device: string; readonly metric: string }>>;
    readonly commands: Readonly<Record<string, readonly CommandSpec[]>>;
  };
  readonly json: { readonly root: string; readonly topics: Readonly<Record<string, JsonTopicSpec>> };
  readonly acl: Readonly<Record<string, { readonly publish: readonly string[]; readonly subscribe: readonly string[] }>>;
};

export const plcIoDoc: PlcIoDoc = plcIo;
export const topicsDoc: TopicsDoc = topics;
