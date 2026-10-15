// Commands, recipe handshake, events and quality against the running line (EDG-03..13 and the
// l2-edge-uns.md acceptance criteria). One fresh plant for the whole file.
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import { randomUUID } from 'node:crypto';
import { jsonTopic } from '@vbp/contracts';
import { UnsClient, connect } from '../src/uns-client.js';
import {
  acknowledgeAlarms,
  freshPlant,
  lineSnapshot,
  realMs,
  startLine,
  stopLine,
} from '../src/plant.js';
import { simApi } from '../src/sim-api.js';
import type { MqttClient } from 'mqtt';

const HELD = 11;
const EXECUTE = 6;
const QUALITY = { good: 192, bad: 0 };

// The PLC's cold-start orange recipe (FB_RecipeHandshake): a download leaves the plant as it
// was, so the FAT suite can run after these tests.
function recipe(overrides: Record<string, unknown> = {}) {
  return {
    ts: new Date().toISOString(),
    source: 'mes-api',
    schemaVersion: '1.0',
    messageId: randomUUID(),
    workOrderNo: 'WO-1042',
    recipeId: 7,
    recipeVersion: 3,
    productCode: 1,
    brixTarget: 11.5,
    brixTol: 0.3,
    concRatio: 0.162,
    fillTargetG: 1005,
    lineSpeed: 120,
    capTorque: 2.2,
    ...overrides,
  };
}

describe('Line 1 through the UNS', () => {
  let uns: UnsClient;
  let mes: MqttClient;

  async function download(body: Record<string, unknown>) {
    const sent = Date.now();
    await mes.publishAsync(jsonTopic('recipe'), JSON.stringify(body), { qos: 1 });
    const result = await uns.waitFor(
      'a recipe result',
      () =>
        uns.since(
          sent,
          (m) => m.topic === jsonTopic('recipe_result') && m.json?.requestId === body.messageId,
        )[0],
      12_000,
    );
    return { ...result.json!, roundTripMs: result.at - sent };
  }

  beforeAll(async () => {
    uns = await UnsClient.open('ignition');
    mes = await connect('mes-api');
    await uns.rebirth();
    await freshPlant(uns);
  });
  afterAll(async () => {
    await simApi.clearFaults();
    await mes.endAsync();
    await uns.close();
  });

  describe('recipe download (EDG-11)', () => {
    it('is acknowledged while the line is stopped, round trip < 2 s', async () => {
      await stopLine(uns);
      const result = await download(recipe());
      expect(result).toMatchObject({
        result: 'Ack',
        recipeId: 7,
        recipeVersion: 3,
        workOrderNo: 'WO-1042',
      });
      expect(result.roundTripMs).toBeLessThan(2000);
      await uns.waitFor('LINE RecipeVersion = 3', () => uns.value('LINE', 'RecipeVersion') === 3);
    });

    it('is rejected by schema before reaching the PLC', async () => {
      expect(await download(recipe({ brixTarget: 20 }))).toMatchObject({ result: 'Invalid' });
    });

    it('is refused with a Nak while the line runs', async () => {
      await startLine(uns);
      expect(await download(recipe({ recipeVersion: 4 }))).toMatchObject({
        result: 'Nak',
        nakCode: 1,
        reason: 'InExecute',
      });
    });
  });

  describe('capper jam (EDG-03, EDG-10)', () => {
    it('publishes C-501 Held with the jam as first-out, and the operator reason reaches the PLC', async () => {
      // First-out = the first alarm raised while the table was clear (ADR 0003). If a process
      // alarm is still active, the jam is correctly not first-out and the line's id stays put.
      const tableClear = await acknowledgeAlarms(uns);
      const firstOutBefore = uns.value('LINE', 'FirstOutAlarmId');
      await uns.waitFor(
        'C-501 in Execute',
        () => uns.value('C501', 'State') === EXECUTE,
        realMs(30),
      );
      const jammed = Date.now();
      await simApi.fault('C501', 'jam', 120);
      const event = await uns.waitFor(
        'a capper Held state event',
        () =>
          uns.since(
            jammed,
            (m) => m.topic === jsonTopic('state', 'capper') && m.json?.state === 'Held',
          )[0],
        realMs(10),
      );
      expect(event.json, lineSnapshot(uns)).toMatchObject({
        device: 'C501',
        stopReason: 10,
        firstOutAlarmId: tableClear ? 10 : firstOutBefore,
      });
      // The first event after the jam leaves a running state (downstream-blocked moments flip the
      // capper between Execute and Suspended). It may be Holding, the acting state before Held,
      // if a poll lands inside it.
      const [first] = uns.since(jammed, (m) => m.topic === jsonTopic('state', 'capper'));
      expect(['Execute', 'Suspended', 'Suspending']).toContain(first?.json?.previousState);
      expect(['Holding', 'Held']).toContain(first?.json?.state);
      expect(uns.value('C501', 'State')).toBe(HELD);
      await uns.waitFor(
        'Alarms/C501_Jam/Active',
        () => uns.value('C501', 'Alarms/C501_Jam/Active') === true,
      );
      if (tableClear) expect(uns.value('C501', 'Alarms/C501_Jam/FirstOut')).toBe(true);
      await uns.waitFor('F-401 blocked', () => uns.value('F401', 'Blocked') === true, realMs(30));

      await uns.command('C501', 'StopReason', 120);
      await uns.waitFor('C501 StopReason = 120', () => uns.value('C501', 'StopReason') === 120);
      await simApi.clearFaults();
    });

    it('rejects a stop reason outside the operator range', async () => {
      await uns.command('C501', 'StopReason', 5);
      await new Promise((r) => setTimeout(r, 1000));
      expect(uns.value('C501', 'StopReason')).not.toBe(5);
    });
  });

  describe('remote I/O loss (EDG-05, SCA-04)', () => {
    it("marks the silent unit's measurements bad and leaves other units good", async () => {
      await simApi.override('TT202_OutTemp', 'disconnect');
      try {
        await uns.waitFor(
          'P-201 CommsOk false',
          () => uns.value('P201', 'CommsOk') === false,
          5_000,
        );
        const quality = (device: string, metric: string) =>
          uns.metrics.get(device)?.get(metric)?.properties?.Quality?.value;
        await uns.waitFor(
          'TT202 bad quality',
          () => quality('P201', 'TT202_OutTemp') === QUALITY.bad,
        );
        expect(quality('P201', 'CommsOk')).toBe(QUALITY.good);
        expect(quality('T301', 'LT301_Level')).toBe(QUALITY.good);
      } finally {
        await simApi.clearOverride('TT202_OutTemp');
      }
    });
  });
});
