import { describe, expect, it } from 'vitest';
import type { MetricDef } from '@vbp/contracts';
import { decodeMetric, joinWords, toSigned16, type PlcSnapshot } from './value-decoder.js';

const snap = (mw: Record<number, number>, md: Record<number, number> = {}): PlcSnapshot => ({
  mw: new Map(Object.entries(mw).map(([k, v]) => [Number(k), v])),
  md: new Map(Object.entries(md).map(([k, v]) => [Number(k), v])),
});
const status = (mw: number, scale = 1, bool = false): MetricDef => ({
  name: 'X',
  type: bool ? 'Boolean' : scale === 1 ? 'Int32' : 'Double',
  source: { kind: 'status', mw, scale, bool },
});

describe('value decoding', () => {
  it('reads signed 16-bit words', () => {
    expect(toSigned16(0x7fff)).toBe(32767);
    expect(toSigned16(0x8000)).toBe(-32768);
    expect(toSigned16(0xffff)).toBe(-1);
  });

  it('joins 32-bit counters high word first', () => {
    expect(joinWords(0x0001, 0x0002)).toBe(65538);
    expect(joinWords(0xffff, 0xffff)).toBe(2 ** 32 - 1);
  });

  it('scales status words', () => {
    expect(decodeMetric(status(61, 10), snap({ 61: 852 }))).toBe(85.2);
    expect(decodeMetric(status(61, 10), snap({ 61: 0xffec }))).toBe(-2); // −20 / 10
    expect(decodeMetric(status(5, 1, true), snap({ 5: 1 }))).toBe(true);
    expect(decodeMetric(status(0), snap({ 0: 6 }))).toBe(6);
  });

  it('decodes alarm-table bits and priority', () => {
    const word = 0b111 | (2 << 8);
    const alarm = (field: 'Active' | 'Acked' | 'FirstOut' | 'Priority'): MetricDef => ({
      name: field,
      type: 'Boolean',
      source: { kind: 'alarm', mw: 610, field },
    });
    expect(decodeMetric(alarm('Active'), snap({ 610: word }))).toBe(true);
    expect(decodeMetric(alarm('Acked'), snap({ 610: 0b101 }))).toBe(false);
    expect(decodeMetric(alarm('FirstOut'), snap({ 610: word }))).toBe(true);
    expect(decodeMetric(alarm('Priority'), snap({ 610: word }))).toBe(2);
  });

  it('reads counters and momentary commands', () => {
    expect(
      decodeMetric(
        { name: 'C', type: 'UInt32', source: { kind: 'counter', md: 5 } },
        snap({}, { 5: 123456 }),
      ),
    ).toBe(123456);
    expect(
      decodeMetric({ name: 'Cmd_Start', type: 'Boolean', source: { kind: 'momentary' } }, snap({})),
    ).toBe(false);
  });

  it('fails loudly on a word missing from the snapshot', () => {
    expect(() => decodeMetric(status(9), snap({}))).toThrow(/%MW9/);
  });
});
