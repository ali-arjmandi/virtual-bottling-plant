// Every Sparkplug metric of Line 1 and the PLC word behind it, derived from plc-io.yaml with the
// naming rules in topics.yaml. The bridge reads and writes with it; the MES and Ignition need
// only the names and types.
import { plcIoDoc, topicsDoc, type PlcIoDoc, type PlcIoMetric, type TopicsDoc } from './contract-types.js';

export type SparkplugType = 'Int32' | 'UInt32' | 'Double' | 'Boolean';

export type AlarmField = 'Active' | 'Acked' | 'FirstOut' | 'Priority';

/** Where a metric's value comes from on the PLC (%MW / %MD numbers, not Modbus addresses). */
export type MetricSource =
  | { kind: 'status'; mw: number; scale: number; bool: boolean }
  | { kind: 'alarm'; mw: number; field: AlarmField }
  | { kind: 'counter'; md: number }
  | { kind: 'momentary' };

/** A DCMD write: integer `value` for momentary commands, else the metric value × scale. */
export type MetricCommand = { mw: number; value?: number; scale: number; range?: readonly number[] };

export type MetricDef = {
  name: string;
  type: SparkplugType;
  source: MetricSource;
  deadband?: number;
  unit?: string;
  enumName?: string;
  command?: MetricCommand;
};

export type MetricCatalog = Record<string, MetricDef[]>;

function statusMetric(base: number, m: PlcIoMetric): MetricDef {
  const scale = m.scale ?? 1;
  const bool = m.type === 'bool';
  const def: MetricDef = {
    name: m.name,
    type: bool ? 'Boolean' : scale === 1 ? 'Int32' : 'Double',
    source: { kind: 'status', mw: base + m.offset, scale, bool },
  };
  if (m.deadband !== undefined) def.deadband = m.deadband;
  if (m.unit !== undefined) def.unit = m.unit;
  if (m.enum !== undefined) def.enumName = m.enum;
  return def;
}

function statusMetrics(plc: PlcIoDoc, device: string): MetricDef[] {
  const block = plc.status[device];
  if (!block) return [];
  const header = block.header ? plc.packaging_header : [];
  const metrics = [...header, ...block.metrics].map((m) => statusMetric(block.base, m));
  const ns = block.nozzle_subgroups;
  if (ns) {
    for (let n = 1; n <= ns.count; n++) {
      ns.fields.forEach((field, i) => {
        const scale = ns.scale[i] ?? 1;
        const offset = ns.first_offset + ns.fields.length * (n - 1) + i;
        metrics.push(statusMetric(block.base, {
          name: `Nozzles/N${String(n).padStart(2, '0')}/${field}`, offset, scale,
        }));
      });
    }
  }
  return metrics;
}

function alarmMetrics(plc: PlcIoDoc, device: string): MetricDef[] {
  const fields: [AlarmField, SparkplugType][] = [
    ['Active', 'Boolean'], ['Acked', 'Boolean'], ['FirstOut', 'Boolean'], ['Priority', 'Int32'],
  ];
  return plc.alarm_table.alarms
    .filter((a) => a.device === device)
    .flatMap((a) => fields.map(([field, type]) => ({
      name: `Alarms/${a.name}/${field}`, type,
      source: { kind: 'alarm' as const, mw: plc.alarm_table.base + a.id, field },
    })));
}

function counterMetrics(plc: PlcIoDoc, uns: TopicsDoc, device: string): MetricDef[] {
  const devices = Object.keys(uns.sparkplug.devices);
  return plc.counters.flatMap((c) => {
    const override = uns.sparkplug.counter_overrides[c.name];
    const prefix = c.name.slice(0, c.name.indexOf('_'));
    const target = override ?? (devices.includes(prefix)
      ? { device: prefix, metric: c.name.slice(prefix.length + 1) } : undefined);
    if (!target) throw new Error(`counter ${c.name}: no device (prefix or counter_overrides)`);
    if (target.device !== device) return [];
    return [{ name: target.metric, type: 'UInt32' as const, source: { kind: 'counter' as const, md: c.md } }];
  });
}

function applyCommands(plc: PlcIoDoc, uns: TopicsDoc, device: string, metrics: MetricDef[]): void {
  const set = uns.sparkplug.devices[device]?.commands;
  if (!set) return;
  const specs = uns.sparkplug.commands[set];
  if (!specs) throw new Error(`${device}: unknown command set ${set}`);
  for (const spec of specs) {
    const wordName = spec.word.replace('{device}', device);
    const word = plc.commands.find((c) => c.name === wordName);
    if (!word) throw new Error(`${device}.${spec.metric}: no plc-io command ${wordName}`);
    const command: MetricCommand = { mw: word.mw, scale: word.scale ?? 1 };
    if (spec.range) command.range = spec.range;
    if (spec.value !== undefined) {
      const values = plc.enums[word.enum ?? ''] ?? {};
      const code = Object.entries(values).find(([, name]) => name === spec.value)?.[0];
      if (code === undefined) throw new Error(`${wordName}: no enum value ${spec.value}`);
      command.value = Number(code);
    }
    const existing = metrics.find((m) => m.name === spec.metric);
    if (existing) existing.command = command;
    else metrics.push({ name: spec.metric, type: spec.type, source: { kind: 'momentary' }, command });
  }
}

export function buildMetricCatalog(plc: PlcIoDoc = plcIoDoc, uns: TopicsDoc = topicsDoc): MetricCatalog {
  const catalog: MetricCatalog = {};
  for (const device of Object.keys(uns.sparkplug.devices)) {
    if (!plc.status[device]) throw new Error(`device ${device}: no status block in plc-io.yaml`);
    const metrics = [
      ...statusMetrics(plc, device), ...alarmMetrics(plc, device), ...counterMetrics(plc, uns, device),
    ];
    applyCommands(plc, uns, device, metrics);
    const names = new Set<string>();
    for (const m of metrics) {
      if (names.has(m.name)) throw new Error(`${device}: duplicate metric ${m.name}`);
      names.add(m.name);
    }
    catalog[device] = metrics;
  }
  return catalog;
}
