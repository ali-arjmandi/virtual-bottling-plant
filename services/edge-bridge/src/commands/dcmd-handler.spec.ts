import { describe, expect, it } from 'vitest';
import { pino } from 'pino';
import { buildMetricCatalog } from '@vbp/contracts';
import type { UMetric } from 'sparkplug-payload/lib/sparkplugbpayload.js';
import { DcmdHandler } from './dcmd-handler.js';

const handler = new DcmdHandler(buildMetricCatalog(), pino({ level: 'silent' }));
const m = (name: string, value: UMetric['value'], type: UMetric['type'] = 'Boolean'): UMetric => ({
  name,
  value,
  type,
});

describe('DcmdHandler', () => {
  it('turns momentary commands into command words', () => {
    expect(handler.handle('C501', [m('Cmd_Reset', true)]).writes).toEqual([
      { mw: 804, values: [3] },
    ]);
    expect(handler.handle('LINE', [m('Cmd_Start', true)]).writes).toEqual([
      { mw: 808, values: [1] },
    ]);
    expect(handler.handle('C501', [m('Cmd_Reset', false)]).writes).toEqual([]);
  });

  it('writes stop reasons and alarm acks', () => {
    expect(handler.handle('F401', [m('StopReason', 120, 'Int32')]).writes).toEqual([
      { mw: 813, values: [120] },
    ]);
    expect(handler.handle('LINE', [m('AlarmAck', -1, 'Int32')]).writes).toEqual([
      { mw: 820, values: [-1] },
    ]);
  });

  it('rejects unknown devices, read-only metrics and out-of-range values', () => {
    expect(handler.handle('X999', [m('Cmd_Start', true)]).writes).toEqual([]);
    expect(handler.handle('P201', [m('TT202_OutTemp', 90, 'Double')]).writes).toEqual([]);
    expect(handler.handle('F401', [m('StopReason', 5, 'Int32')]).writes).toEqual([]);
    expect(handler.handle('F401', [m('Cmd_Start', 1, 'Int32')]).writes).toEqual([]);
  });

  it('handles the node rebirth request', () => {
    expect(handler.handle(null, [m('Node Control/Rebirth', true)])).toEqual({
      writes: [],
      rebirth: true,
    });
    expect(handler.handle(null, [m('Node Control/Reboot', true)]).rebirth).toBe(false);
  });
});
