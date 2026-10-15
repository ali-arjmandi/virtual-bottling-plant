// EDG-01/02/06: every Line 1 device births with the metrics of the contract, DDATA follows,
// and timestamps are sim time.
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import { buildMetricCatalog, topicsDoc } from '@vbp/contracts';
import { UnsClient } from '../src/uns-client.js';
import { testEnv } from '../src/test-env.js';

const devices = Object.keys(topicsDoc.sparkplug.devices);
const catalog = buildMetricCatalog();

describe('Sparkplug B telemetry', () => {
  let uns: UnsClient;
  let t0: number;

  beforeAll(async () => {
    uns = await UnsClient.open('ignition');
    t0 = Date.now();
    await uns.rebirth();
    await uns.waitFor(
      'a DBIRTH from every device',
      () =>
        devices.every(
          (d) => uns.since(t0, (m) => m.topic.endsWith(`/DBIRTH/Line1/${d}`)).length > 0,
        ),
      5_000,
    );
  });
  afterAll(() => uns.close());

  it('births the node with bdSeq and the rebirth control', () => {
    const [nbirth] = uns.since(t0, (m) => m.topic.endsWith('/NBIRTH/Line1'));
    const names = nbirth?.sparkplug?.metrics?.map((m) => m.name);
    expect(names).toEqual(['bdSeq', 'Node Control/Rebirth']);
    expect(Number(nbirth?.sparkplug?.seq)).toBe(0);
  });

  it.each(devices)('%s births every contract metric with a quality', (device) => {
    const [birth] = uns.since(t0, (m) => m.topic.endsWith(`/DBIRTH/Line1/${device}`));
    const metrics = birth?.sparkplug?.metrics ?? [];
    expect(metrics.map((m) => m.name).sort()).toEqual(catalog[device]!.map((m) => m.name).sort());
    expect(metrics.every((m) => m.properties?.Quality !== undefined)).toBe(true);
  });

  it('sends DDATA after the births, with increasing seq', async () => {
    await uns.waitFor('DDATA', () => uns.since(t0, (m) => m.topic.includes('/DDATA/')).length >= 3);
    const seqs = uns
      .since(t0, (m) => m.topic.includes('/DBIRTH/') || m.topic.includes('/DDATA/'))
      .map((m) => Number(m.sparkplug?.seq));
    for (let i = 1; i < seqs.length; i++) expect(seqs[i]).toBe((seqs[i - 1]! + 1) % 256);
  });

  it('timestamps with the sim clock (SIM_EPOCH + SimTimeMs)', () => {
    const [birth] = uns.since(t0, (m) => m.topic.endsWith('/DBIRTH/Line1/LINE'));
    const simTime = Number(birth?.sparkplug?.metrics?.find((m) => m.name === 'SimTimeMs')?.value);
    const epoch = Date.parse(process.env.SIM_EPOCH ?? '2026-10-05T05:30:00Z');
    expect(Number(birth?.sparkplug?.timestamp)).toBe(epoch + simTime);
    expect(testEnv.simSpeed).toBeGreaterThan(0);
  });
});
