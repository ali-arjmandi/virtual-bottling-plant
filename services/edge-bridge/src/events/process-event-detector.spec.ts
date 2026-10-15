import { describe, expect, it } from 'vitest';
import { ProcessEventDetector } from './process-event-detector.js';
import { lineValues } from './test-values.js';

const values = (batchActive: boolean, divert: boolean) =>
  lineValues({
    T101: {
      BatchActive: batchActive,
      BatchNo: 4,
      ProductCode: 1,
      ConcLotNo: 2031,
      BatchBrix: 11.62,
      BrixOk: true,
    },
    P201: { XV203_Divert: divert, DivertCount: 2, TT202_OutTemp: 82.4 },
  });

describe('ProcessEventDetector', () => {
  it('emits nothing on the first poll', () => {
    expect(new ProcessEventDetector().detect(values(true, true))).toEqual({
      batch: [],
      divert: [],
    });
  });

  it('emits batch start and end, with Brix only at the end', () => {
    const d = new ProcessEventDetector();
    d.detect(values(false, false));
    expect(d.detect(values(true, false)).batch).toEqual([
      {
        event: 'start',
        batchNo: 4,
        productCode: 1,
        concentrateLotNo: 2031,
        brix: null,
        brixOk: null,
      },
    ]);
    expect(d.detect(values(false, false)).batch[0]).toMatchObject({
      event: 'end',
      brix: 11.62,
      brixOk: true,
    });
  });

  it('emits divert start and end', () => {
    const d = new ProcessEventDetector();
    d.detect(values(true, false));
    expect(d.detect(values(true, true)).divert).toEqual([
      { event: 'start', divertCount: 2, outTempC: 82.4, batchNo: 4 },
    ]);
    expect(d.detect(values(true, false)).divert[0]).toMatchObject({ event: 'end' });
  });
});
