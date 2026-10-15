// The simulator's REST API (contracts.md §4), for setting up scenarios.
import { testEnv } from './test-env.js';

async function call(method: string, path: string, body?: unknown): Promise<unknown> {
  const res = await fetch(`${testEnv.simUrl}${path}`, {
    method,
    headers: { 'content-type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`sim ${method} ${path}: ${res.status} ${await res.text()}`);
  return res.status === 204 ? null : res.json();
}

export const simApi = {
  reset: (seed = 42) => call('POST', '/reset', { seed, randomFaults: false }),
  clock: (speed: number) => call('POST', '/clock', { speed, paused: false }),
  fault: (machine: string, type: string, durationS?: number) =>
    call('POST', '/faults', { machine, type, ...(durationS === undefined ? {} : { durationS }) }),
  override: (tag: string, mode: 'stuck' | 'disconnect' | 'noise') =>
    call('POST', `/sensors/${tag}/override`, { mode }),
  clearOverride: (tag: string) => call('DELETE', `/sensors/${tag}/override`),
  clearFaults: async () => {
    const state = (await call('GET', '/state')) as { faults: { id: number }[] };
    for (const f of state.faults) await call('DELETE', `/faults/${f.id}`);
  },
};
