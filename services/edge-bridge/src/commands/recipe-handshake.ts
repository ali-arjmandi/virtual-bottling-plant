// Recipe download handshake with the PLC (contracts.md §2, EDG-11), as a pure state machine:
// the caller feeds requests and poll results and carries out the returned actions in order.
//   idle ─request→ requested ─Ack | Nak | 10 s→ clearing ─Ack and Nak back to 0→ idle
import type { RecipeCommand, RecipeResult } from '@vbp/contracts';
import type { EventBody } from '../events/event-publisher.js';
import {
  NAK_BUSY,
  RECIPE_REQ_MW,
  RECIPE_TIMEOUT_MS,
  nakName,
  recipeWrites,
  type WordWrite,
} from './recipe-words.js';

export type RecipeResultBody = EventBody<RecipeResult>;
export type HandshakeAction =
  { kind: 'write'; write: WordWrite } | { kind: 'result'; body: RecipeResultBody };
export type RecipeResponse = { ack: boolean; nak: number };

type Pending = { cmd: RecipeCommand; startedMs: number };

export class RecipeHandshake {
  private phase: 'idle' | 'requested' | 'clearing' = 'idle';
  private pending: Pending | null = null;
  private clearingSinceMs = 0;

  get state(): string {
    return this.phase;
  }

  request(cmd: RecipeCommand, nowMs: number): HandshakeAction[] {
    if (this.phase !== 'idle') {
      return [{ kind: 'result', body: resultBody(cmd, 'Nak', NAK_BUSY, nakName(NAK_BUSY), 0) }];
    }
    this.phase = 'requested';
    this.pending = { cmd, startedMs: nowMs };
    return [
      ...recipeWrites(cmd).map((write) => ({ kind: 'write' as const, write })),
      { kind: 'write', write: { mw: RECIPE_REQ_MW, values: [1] } },
    ];
  }

  poll(response: RecipeResponse, nowMs: number): HandshakeAction[] {
    if (this.phase === 'requested' && this.pending) {
      const { cmd, startedMs } = this.pending;
      const elapsed = nowMs - startedMs;
      let body: RecipeResultBody | null = null;
      if (response.ack) body = resultBody(cmd, 'Ack', null, null, elapsed);
      else if (response.nak > 0)
        body = resultBody(cmd, 'Nak', response.nak, nakName(response.nak), elapsed);
      else if (elapsed >= RECIPE_TIMEOUT_MS)
        body = resultBody(cmd, 'Timeout', null, 'no Ack/Nak within 10 s', elapsed);
      if (!body) return [];
      this.phase = 'clearing';
      this.pending = null;
      this.clearingSinceMs = nowMs;
      return [
        { kind: 'result', body },
        { kind: 'write', write: { mw: RECIPE_REQ_MW, values: [0] } },
      ];
    }
    if (this.phase === 'clearing') {
      const cleared = !response.ack && response.nak === 0;
      if (cleared || nowMs - this.clearingSinceMs >= RECIPE_TIMEOUT_MS) this.phase = 'idle';
    }
    return [];
  }
}

export function resultBody(
  cmd: Pick<RecipeCommand, 'messageId' | 'recipeId' | 'recipeVersion' | 'workOrderNo'>,
  result: RecipeResult['result'],
  nakCode: number | null,
  reason: string | null,
  durationMs: number,
): RecipeResultBody {
  const body: RecipeResultBody = {
    requestId: cmd.messageId,
    recipeId: cmd.recipeId,
    recipeVersion: cmd.recipeVersion,
    result,
    nakCode,
    reason,
    durationMs: Math.max(0, Math.round(durationMs)),
  };
  if (cmd.workOrderNo !== undefined) body.workOrderNo = cmd.workOrderNo;
  return body;
}
