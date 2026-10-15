// EDG-05 acceptance: stopping the PLC container gives DDEATH (bad quality in Ignition) within
// 1 s of the 3rd missed poll; recovery re-births. Run on its own (pnpm test:link-loss): it stops
// the PLC.
import { exec } from 'node:child_process';
import { promisify } from 'node:util';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import { topicsDoc } from '@vbp/contracts';
import { UnsClient, type Received } from '../src/uns-client.js';
import { testEnv } from '../src/test-env.js';

const devices = Object.keys(topicsDoc.sparkplug.devices);
const POLL_MS = 250;
const STALE = 500;
// Async, so MQTT messages are timestamped while the container is stopping.
const compose = (args: string) => promisify(exec)(`docker compose ${args}`, { cwd: testEnv.repo });

const isStaleData = (m: Received) =>
  m.topic.includes('/DDATA/') &&
  (m.sparkplug?.metrics ?? []).some((x) => x.properties?.Quality?.value === STALE);

describe('PLC link loss', () => {
  let uns: UnsClient;
  beforeAll(async () => {
    uns = await UnsClient.open('ignition');
  });
  afterAll(async () => {
    await compose('start plc');
    await uns.close();
  });

  it('declares every device dead within 1 s of the 3rd missed poll, and re-births', async () => {
    const stopping = Date.now();
    await compose('stop plc');
    const deaths = await uns.waitFor(
      'DDEATH from every device',
      () => {
        const d = uns.since(stopping, (m) => m.topic.includes('/DDEATH/'));
        return d.length >= devices.length && d;
      },
      10_000,
    );
    // The first missed poll publishes stale quality; the 3rd follows two polls later.
    const firstMiss = uns.since(stopping, isStaleData)[0]?.at;
    expect(firstMiss).toBeDefined();
    const thirdMiss = firstMiss! + 2 * POLL_MS;
    expect(Math.max(...deaths.map((d) => d.at)) - thirdMiss).toBeLessThan(1000);

    const started = Date.now();
    await compose('start plc');
    await uns.waitFor(
      'DBIRTH from every device',
      () => uns.since(started, (m) => m.topic.includes('/DBIRTH/')).length >= devices.length,
      60_000,
    );
  }, 90_000);
});
