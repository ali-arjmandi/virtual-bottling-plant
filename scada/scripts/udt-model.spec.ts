import { describe, expect, it } from 'vitest';
import { buildMetricCatalog, plcIoDoc } from '@vbp/contracts';
import { UDT_BY_DEVICE, buildInstances, buildUdts, instancePath } from './udt-model.js';
import type { TagJson } from './tag-json.js';

const catalog = buildMetricCatalog();
const udts = buildUdts(catalog);
const byName = (name: string) => udts.find((u) => u.name === name)!;

/** Leaf tags of a UDT with their folder path, following inheritance and nozzle sub-instances. */
function leaves(tags: TagJson[] = [], prefix = ''): Map<string, TagJson> {
  const out = new Map<string, TagJson>();
  for (const t of tags) {
    const path = `${prefix}${t.name}`;
    if (t.tagType === 'Folder') for (const [k, v] of leaves(t.tags, `${path}/`)) out.set(k, v);
    else if (t.tagType === 'UdtInstance')
      for (const [k, v] of leaves(byName(t.typeId!).tags, `${path}/`)) out.set(k, v);
    else out.set(path, t);
  }
  return out;
}
const members = (udt: TagJson) =>
  new Map([...(udt.typeId ? leaves(byName(udt.typeId).tags) : []), ...leaves(udt.tags)]);

describe('generated UDTs', () => {
  it.each(Object.keys(catalog))('%s: every contract metric is a member', (device) => {
    const names = [...members(byName(UDT_BY_DEVICE[device]!)).keys()];
    for (const def of catalog[device]!) expect(names).toContain(def.name);
  });

  it('references MQTT Engine by the Device parameter', () => {
    const state = leaves(byName('UDT_PackMLMachine').tags).get('State')!;
    expect(state.sourceTagPath).toEqual({
      bindType: 'parameter',
      binding: '[MQTT Engine]Edge Nodes/DelftsSap/Line1/{Device}/State',
    });
    expect(state.dataType).toBe('Int4');
  });

  it('puts every PLC alarm on its Active member with the mapped priority and an ack script', () => {
    const alarms = udts.flatMap((u) => [...leaves(u.tags).values()]).filter((t) => t.alarms);
    expect(alarms).toHaveLength(plcIoDoc.alarm_table.alarms.length);
    const jam = leaves(byName('UDT_Capper').tags).get('Alarms/C501_Jam/Active')!;
    expect(jam.alarms?.[0]).toMatchObject({
      name: 'C501_Jam',
      priority: 'High',
      label: 'Capper jam',
    });
    expect(jam.eventScripts?.[0]?.script).toContain('AlarmAck"], [10])');
  });

  it('gives packaging machines the PackML base and the stop-reason members', () => {
    expect(byName('UDT_Filler').typeId).toBe('UDT_PackMLMachine');
    const base = leaves(byName('UDT_PackMLMachine').tags);
    expect([...base.keys()]).toEqual(
      expect.arrayContaining(['StateText', 'NotRunningSinceMs', 'ReasonNeeded']),
    );
    expect(base.get('State')?.eventScripts?.[0]?.eventid).toBe('valueChanged');
    expect(leaves(byName('UDT_Line').tags).get('State')?.eventScripts).toBeUndefined();
  });

  it('records history for measurements and counters only', () => {
    const pasteurizer = leaves(byName('UDT_Pasteurizer').tags);
    expect(pasteurizer.get('TT202_OutTemp')).toMatchObject({ historyEnabled: true, engUnit: '°C' });
    expect(pasteurizer.get('XV203_Divert')?.historyEnabled).toBeUndefined();
  });

  it('builds 12 checkweigher nozzles from one nozzle UDT', () => {
    const nozzles = byName('UDT_Checkweigher').tags!.find((t) => t.name === 'Nozzles')!;
    expect(nozzles.tags).toHaveLength(12);
    expect(nozzles.tags![11]).toMatchObject({ name: 'N12', typeId: 'UDT_Nozzle' });
  });
});

describe('instances', () => {
  it('places each device in the ISA-95 folders (SCA-03)', () => {
    expect(instancePath('P201')).toBe('Delft/Process/Line1/P201');
    expect(instancePath('LINE')).toBe('Delft/Packaging/Line1/Line');
    const line1 = buildInstances(catalog)[0]!.tags!.find((t) => t.name === 'Packaging')!.tags![0]!;
    expect(line1.tags!.map((t) => t.name)).toEqual([
      'F401',
      'C501',
      'L601',
      'Q701',
      'K801',
      'Line',
    ]);
    expect(line1.tags![1]).toMatchObject({
      typeId: 'UDT_Capper',
      parameters: { Device: { value: 'C501' } },
    });
  });
});
