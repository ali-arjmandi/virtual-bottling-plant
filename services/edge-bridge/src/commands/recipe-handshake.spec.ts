import { describe, expect, it } from 'vitest';
import { RecipeHandshake, type HandshakeAction } from './recipe-handshake.js';
import { recipeCommand } from './test-recipe.js';

const writes = (a: HandshakeAction[]) =>
  a.filter((x) => x.kind === 'write').map((x) => x.kind === 'write' && x.write);
const result = (a: HandshakeAction[]) => a.find((x) => x.kind === 'result');
const idle = { ack: false, nak: 0 };

describe('RecipeHandshake', () => {
  it('writes values, then Req, then clears Req on Ack', () => {
    const h = new RecipeHandshake();
    const start = h.request(recipeCommand, 0);
    expect(writes(start).map((w) => w && w.mw)).toEqual([903, 900]);
    expect(h.poll(idle, 250)).toEqual([]);
    const done = h.poll({ ack: true, nak: 0 }, 500);
    expect(result(done)).toMatchObject({
      body: {
        result: 'Ack',
        requestId: recipeCommand.messageId,
        recipeId: 7,
        recipeVersion: 3,
        workOrderNo: 'WO-1042',
        nakCode: null,
        durationMs: 500,
      },
    });
    expect(writes(done)).toEqual([{ mw: 900, values: [0] }]);
    expect(h.state).toBe('clearing');
    h.poll({ ack: true, nak: 0 }, 750);
    expect(h.state).toBe('clearing');
    h.poll(idle, 1000);
    expect(h.state).toBe('idle');
  });

  it('reports a Nak with its name', () => {
    const h = new RecipeHandshake();
    h.request(recipeCommand, 0);
    expect(result(h.poll({ ack: false, nak: 1 }, 300))).toMatchObject({
      body: { result: 'Nak', nakCode: 1, reason: 'InExecute' },
    });
  });

  it('times out after 10 s and clears Req', () => {
    const h = new RecipeHandshake();
    h.request(recipeCommand, 0);
    expect(h.poll(idle, 9_999)).toEqual([]);
    const timeout = h.poll(idle, 10_000);
    expect(result(timeout)).toMatchObject({ body: { result: 'Timeout' } });
    expect(writes(timeout)).toEqual([{ mw: 900, values: [0] }]);
  });

  it('answers Busy to a second request during a handshake', () => {
    const h = new RecipeHandshake();
    h.request(recipeCommand, 0);
    const busy = h.request({ ...recipeCommand, messageId: 'other' }, 100);
    expect(writes(busy)).toEqual([]);
    expect(result(busy)).toMatchObject({
      body: { result: 'Nak', reason: 'Busy', requestId: 'other' },
    });
  });

  it('returns to idle even if the PLC never clears its response', () => {
    const h = new RecipeHandshake();
    h.request(recipeCommand, 0);
    h.poll({ ack: true, nak: 0 }, 100);
    h.poll({ ack: true, nak: 0 }, 10_100);
    expect(h.state).toBe('idle');
  });
});
