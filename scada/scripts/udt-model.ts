// Ignition UDTs and instances for Line 1, derived from the contract metric catalog, so the HMI
// tags can never drift from the PLC map (SCA-01..03). Members are reference tags to the tags MQTT
// Engine builds from the Sparkplug births, so their quality passes through as is (SCA-04).
import {
  buildMetricCatalog,
  plcIoDoc,
  topicsDoc,
  type MetricCatalog,
  type MetricDef,
} from '@vbp/contracts';
import { DATA_TYPES, param, placeAt, type AlarmJson, type TagJson } from './tag-json.js';
import {
  STATE_CHANGE_SCRIPT,
  alarmAckScript,
  lineDerivedMembers,
  packmlDerivedMembers,
} from './derived-members.js';

export const MQTT_ROOT = `[MQTT Engine]Edge Nodes/${topicsDoc.sparkplug.group}/${topicsDoc.sparkplug.node}`;
export const HISTORY_PROVIDER = 'SCADA';
const PACKML_BASE = 'UDT_PackMLMachine';

/** One UDT per equipment type; the packaging machines inherit the PackML base. */
export const UDT_BY_DEVICE: Record<string, string> = {
  T101: 'UDT_MixTank',
  P201: 'UDT_Pasteurizer',
  T301: 'UDT_Tank',
  F401: 'UDT_Filler',
  C501: 'UDT_Capper',
  L601: 'UDT_Labeler',
  Q701: 'UDT_Checkweigher',
  K801: 'UDT_CasePacker',
  LINE: 'UDT_Line',
};

const PRIORITY: Record<number, AlarmJson['priority']> = {
  1: 'Critical',
  2: 'High',
  3: 'Medium',
  4: 'Low',
};
const BASE_COMMANDS = ['Cmd_Start', 'Cmd_Stop', 'Cmd_Reset'];
const basePackml = new Set([...plcIoDoc.packaging_header.map((m) => m.name), ...BASE_COMMANDS]);

const isPackaging = (device: string) => plcIoDoc.status[device]?.header !== undefined;

/** Where the instance lives in the ISA-95 folder tree (SCA-03). */
export function instancePath(device: string): string {
  const area = topicsDoc.sparkplug.devices[device]?.area === 'process' ? 'Process' : 'Packaging';
  return `Delft/${area}/Line1/${device === 'LINE' ? 'Line' : device}`;
}

function alarmFor(metricName: string): TagJson['alarms'] {
  const match = /^Alarms\/(.+)\/Active$/.exec(metricName);
  const alarm = match && plcIoDoc.alarm_table.alarms.find((a) => a.name === match[1]);
  if (!alarm) return undefined;
  return [
    {
      name: alarm.name,
      label: alarm.text,
      priority: PRIORITY[alarm.priority] ?? 'Low',
      mode: 'Equality',
      setpointA: 1,
      ackMode: 'Manual',
      displayPath: param('Line1/{Device}'),
    },
  ];
}

function member(def: MetricDef): Omit<TagJson, 'name'> {
  const tag: Omit<TagJson, 'name'> = {
    tagType: 'AtomicTag',
    dataType: DATA_TYPES[def.type],
    valueSource: 'reference',
    sourceTagPath: param(`${MQTT_ROOT}/{Device}/${def.name}`),
  };
  if (def.unit) tag.engUnit = def.unit;
  if (def.unit || def.source.kind === 'counter') {
    tag.historyEnabled = true;
    tag.historyProvider = HISTORY_PROVIDER;
  }
  const alarms = alarmFor(def.name);
  if (alarms) {
    tag.alarms = alarms;
    const id = plcIoDoc.alarm_table.alarms.find((a) => a.name === alarms[0]!.name)!.id;
    tag.eventScripts = [{ eventid: 'alarmAcked', script: alarmAckScript(id) }];
  }
  return tag;
}

const isPackagingMember = (def: MetricDef) => basePackml.has(def.name);

function udt(name: string, members: MetricDef[], extra: TagJson[] = [], typeId?: string): TagJson {
  const tags: TagJson[] = [];
  for (const def of members.filter((m) => !m.name.startsWith('Nozzles/')))
    placeAt(tags, def.name, member(def));
  tags.push(...extra);
  const type: TagJson = {
    name,
    tagType: 'UdtType',
    parameters: { Device: { dataType: 'String', value: '' } },
    tags,
  };
  if (typeId) type.typeId = typeId;
  return type;
}

function nozzleUdt(q701: MetricDef[]): TagJson {
  const fields = q701.filter((m) => m.name.startsWith('Nozzles/N01/'));
  const tags = fields.map((f) => {
    const field = f.name.split('/').pop()!;
    return {
      name: field,
      ...member({ ...f, name: field }),
      sourceTagPath: param(`${MQTT_ROOT}/{Device}/Nozzles/{Nozzle}/${field}`),
    };
  });
  return {
    name: 'UDT_Nozzle',
    tagType: 'UdtType',
    parameters: {
      Device: { dataType: 'String', value: '' },
      Nozzle: { dataType: 'String', value: '' },
    },
    tags,
  };
}

function nozzleInstances(q701: MetricDef[]): TagJson {
  const nozzles = [
    ...new Set(q701.filter((m) => m.name.startsWith('Nozzles/')).map((m) => m.name.split('/')[1]!)),
  ];
  return {
    name: 'Nozzles',
    tagType: 'Folder',
    tags: nozzles.map((n) => ({
      name: n,
      tagType: 'UdtInstance',
      typeId: 'UDT_Nozzle',
      parameters: {
        Device: { dataType: 'String', value: param('{Device}') },
        Nozzle: { dataType: 'String', value: n },
      },
    })),
  };
}

/** Every UDT definition, base types first. */
export function buildUdts(catalog: MetricCatalog = buildMetricCatalog()): TagJson[] {
  const f401 = catalog.F401!;
  const base = udt(PACKML_BASE, f401.filter(isPackagingMember), packmlDerivedMembers());
  const state = base.tags!.find((t) => t.name === 'State')!;
  state.eventScripts = [{ eventid: 'valueChanged', script: STATE_CHANGE_SCRIPT }];
  const types: TagJson[] = [base, nozzleUdt(catalog.Q701!)];
  const machinePaths = Object.keys(catalog)
    .filter(isPackaging)
    .map((d) => `[default]${instancePath(d)}`);
  for (const [device, defs] of Object.entries(catalog)) {
    const name = UDT_BY_DEVICE[device]!;
    if (isPackaging(device)) {
      const extra = device === 'Q701' ? [nozzleInstances(defs)] : [];
      types.push(
        udt(
          name,
          defs.filter((d) => !isPackagingMember(d)),
          extra,
          PACKML_BASE,
        ),
      );
    } else {
      types.push(udt(name, defs, device === 'LINE' ? lineDerivedMembers(machinePaths) : []));
    }
  }
  return types;
}

/** The Line 1 instances in the ISA-95 folder tree. */
export function buildInstances(catalog: MetricCatalog = buildMetricCatalog()): TagJson[] {
  const root: TagJson[] = [];
  for (const device of Object.keys(catalog)) {
    placeAt(root, instancePath(device), {
      tagType: 'UdtInstance',
      typeId: UDT_BY_DEVICE[device]!,
      parameters: { Device: { dataType: 'String', value: device } },
    });
  }
  return root;
}
