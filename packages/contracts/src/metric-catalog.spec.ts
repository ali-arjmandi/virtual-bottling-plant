import { describe, expect, it } from 'vitest';
import { plcIoDoc, topicsDoc } from './contract-types.js';
import { buildMetricCatalog, type MetricDef } from './metric-catalog.js';

const catalog = buildMetricCatalog();
const metric = (device: string, name: string): MetricDef => {
  const m = catalog[device]?.find((x) => x.name === name);
  if (!m) throw new Error(`${device}/${name} missing`);
  return m;
};

describe('buildMetricCatalog', () => {
  it('has every Sparkplug device', () => {
    expect(Object.keys(catalog).sort()).toEqual(Object.keys(topicsDoc.sparkplug.devices).sort());
  });

  it('maps a scaled process value to its status word', () => {
    expect(metric('P201', 'TT202_OutTemp')).toMatchObject({
      type: 'Double', deadband: 0.1, unit: '°C',
      source: { kind: 'status', mw: 61, scale: 10, bool: false },
    });
  });

  it('gives packaging machines the header at their base', () => {
    expect(metric('C501', 'State')).toMatchObject({ type: 'Int32', enumName: 'PackMLState', source: { mw: 200 } });
    expect(metric('K801', 'Blocked')).toMatchObject({ type: 'Boolean', source: { mw: 355, bool: true } });
  });

  it('expands the Q701 nozzle subgroups', () => {
    expect(metric('Q701', 'Nozzles/N01/Seq').source).toMatchObject({ mw: 314, scale: 1 });
    expect(metric('Q701', 'Nozzles/N12/Range')).toMatchObject({ type: 'Double', source: { mw: 349, scale: 10 } });
  });

  it('puts alarms on their device at 600 + id', () => {
    expect(metric('C501', 'Alarms/C501_Jam/FirstOut').source).toEqual({ kind: 'alarm', mw: 610, field: 'FirstOut' });
    const alarmCount = Object.values(catalog).flat().filter((m) => m.source.kind === 'alarm').length;
    expect(alarmCount).toBe(plcIoDoc.alarm_table.alarms.length * 4);
  });

  it('strips the device prefix from counters and applies overrides', () => {
    expect(metric('Q701', 'GoodCount')).toMatchObject({ type: 'UInt32', source: { kind: 'counter', md: 5 } });
    expect(metric('LINE', 'SimTimeMs').source).toEqual({ kind: 'counter', md: 8 });
    expect(metric('T101', 'ConcLotNo').source).toEqual({ kind: 'counter', md: 7 });
  });

  it('makes command metrics writable', () => {
    expect(metric('F401', 'Cmd_Start')).toMatchObject({
      type: 'Boolean', source: { kind: 'momentary' }, command: { mw: 803, value: 1 },
    });
    expect(metric('LINE', 'Cmd_Stop').command).toMatchObject({ mw: 808, value: 2 });
    expect(metric('C501', 'StopReason')).toMatchObject({
      source: { kind: 'status', mw: 202 }, command: { mw: 814, range: [100, 32767] },
    });
    expect(metric('LINE', 'AlarmAck').command).toEqual({ mw: 820, scale: 1 });
    expect(catalog.P201?.some((m) => m.command)).toBe(false);
  });

  it('rejects a command word missing from plc-io', () => {
    const uns = structuredClone(topicsDoc) as typeof topicsDoc;
    (uns.sparkplug.commands.line as unknown as { word: string }[])[0]!.word = 'NOPE_Cmd';
    expect(() => buildMetricCatalog(plcIoDoc, uns)).toThrow(/NOPE_Cmd/);
  });
});
