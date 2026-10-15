// UNS-02: one user per client, ACL from contracts/uns/topics.yaml, deny by default.
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import type { MqttClient } from 'mqtt';
import { connect } from '../src/uns-client.js';

describe('broker ACL', () => {
  let mes: MqttClient;
  beforeAll(async () => {
    mes = await connect('mes-api');
  });
  afterAll(async () => {
    await mes.endAsync();
  });

  it('refuses a mes-api attempt to publish DCMD', async () => {
    await expect(
      mes.publishAsync('spBv1.0/DelftsSap/DCMD/Line1/F401', 'x', { qos: 1 }),
    ).rejects.toThrow(/Not authorized/);
  });

  it('refuses mes-api publishing telemetry or bridge events', async () => {
    await expect(
      mes.publishAsync('spBv1.0/DelftsSap/DDATA/Line1/F401', 'x', { qos: 1 }),
    ).rejects.toThrow(/Not authorized/);
    await expect(
      mes.publishAsync('delftssap/delft/packaging/line1/capper/state', '{}', { qos: 1 }),
    ).rejects.toThrow(/Not authorized/);
  });

  it('lets mes-api publish its own work-order events', async () => {
    await expect(
      mes.publishAsync('delftssap/delft/packaging/line1/events/workorder', '{}', { qos: 1 }),
    ).resolves.toBeDefined();
  });

  it('refuses a wrong password', async () => {
    await expect(connect('mes-api', 'wrong')).rejects.toThrow(
      /Bad User Name or Password|Not authorized/,
    );
  });
});
