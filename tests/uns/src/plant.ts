// Brings the plant to a known state through the UNS: fresh sim, first batch in T-301, then the
// line started with HMI-style DCMD commands (as tests/fat/conftest.py does over Modbus).
import { simApi } from './sim-api.js';
import { testEnv } from './test-env.js';
import type { UnsClient } from './uns-client.js';

export const MACHINES = ['F401', 'C501', 'L601', 'Q701', 'K801'];
const EXECUTE = 6;
const STOPPED = 2;

/** Real-time budget for a sim duration at the test speed, plus margin. */
export const realMs = (simSeconds: number, marginS = 5) =>
  (simSeconds / testEnv.simSpeed + marginS) * 1000;

function simTimeMs(uns: UnsClient): number | undefined {
  const value = uns.value('LINE', 'SimTimeMs');
  return value === undefined ? undefined : Number(value);
}

export async function freshPlant(uns: UnsClient): Promise<void> {
  const before = await uns.waitFor('the sim clock', () => simTimeMs(uns));
  await simApi.reset(42);
  await simApi.clock(testEnv.simSpeed);
  // The PLC sees the reset one poll later, and the bridge another poll after that: wait until
  // the sim clock read through the PLC has gone back, let its logic settle, then take a fresh
  // birth. Anything cached before that is the old plant.
  await uns.waitFor('the PLC to see the sim reset', () => (simTimeMs(uns) ?? before) < before);
  await new Promise((r) => setTimeout(r, 1000));
  uns.metrics.clear();
  const reset = Date.now();
  await uns.rebirth();
  await uns.waitFor(
    'a DBIRTH after the sim reset',
    () => uns.since(reset, (m) => m.topic.endsWith('/DBIRTH/Line1/LINE')).length > 0,
  );
  await uns.command('LINE', 'Cmd_Stop', true);
  await uns.waitFor(
    'comms to every unit',
    () =>
      [...uns.metrics.keys()].length === 9 &&
      [...uns.metrics.keys()].every((d) => uns.value(d, 'CommsOk') === true),
    20_000,
  );
  await uns.waitFor(
    'a first batch in T-301 with P-201 in forward flow',
    () =>
      uns.value('T301', 'FillerPermissive') === true && uns.value('P201', 'ForwardFlowOk') === true,
    realMs(3600),
  );
}

export async function stopLine(uns: UnsClient): Promise<void> {
  await uns.command('LINE', 'Cmd_Stop', true);
  await uns.waitFor('the line Stopped', () => uns.value('F401', 'State') === STOPPED, realMs(60));
}

/** Machine states and reasons, for failure messages. */
export function lineSnapshot(uns: UnsClient): string {
  const machines = MACHINES.map(
    (m) => `${m}=${uns.value(m, 'State')}/r${uns.value(m, 'StopReason')}`,
  ).join(' ');
  return `${machines} firstOut=${uns.value('LINE', 'FirstOutAlarmId')} T301=${uns.value('T301', 'LT301_Level')}%`;
}

async function withSnapshot<T>(uns: UnsClient, step: Promise<T>): Promise<T> {
  try {
    return await step;
  } catch (err) {
    throw new Error(`${(err as Error).message} [${lineSnapshot(uns)}]`);
  }
}

export async function startLine(uns: UnsClient): Promise<void> {
  await uns.command('LINE', 'Cmd_Reset', true);
  await new Promise((r) => setTimeout(r, 300));
  await uns.command('LINE', 'Cmd_Start', true);
  await withSnapshot(
    uns,
    uns.waitFor(
      'every packaging machine in Execute',
      () => MACHINES.every((m) => uns.value(m, 'State') === EXECUTE),
      realMs(120),
    ),
  );
  await acknowledgeAlarms(uns);
}

/**
 * Acknowledges every alarm. Start-up alarms (e.g. the first P-201 divert) stay latched as
 * first-out until then. Returns whether the table came clear: it cannot while a process alarm
 * is still active (e.g. a batch out of Brix spec, which the sim produces on purpose).
 */
export async function acknowledgeAlarms(uns: UnsClient): Promise<boolean> {
  await uns.command('LINE', 'AlarmAck', -1);
  try {
    await uns.waitFor(
      'a clear alarm table',
      () => uns.value('LINE', 'FirstOutAlarmId') === 0,
      3_000,
    );
    return true;
  } catch {
    return false;
  }
}
