import { describe, expect, it } from 'vitest';
import { validateMessage } from './validators.js';

const envelope = {
  ts: '2026-10-05T06:00:00.000Z', source: 'mes-api', schemaVersion: '1.0',
  messageId: '6f1c7a52-3f6e-4c39-9f43-0d1f1d2b6a11',
};
const recipe = {
  ...envelope, workOrderNo: 'WO-1042', recipeId: 7, recipeVersion: 3, productCode: 1,
  brixTarget: 11.5, brixTol: 0.3, concRatio: 0.162, fillTargetG: 1005, lineSpeed: 120, capTorque: 2.2,
};

describe('validateMessage', () => {
  it('accepts a valid recipe command', () => {
    expect(validateMessage('recipe-command', recipe)).toBeNull();
  });

  it('rejects out-of-range values and missing envelope fields', () => {
    expect(validateMessage('recipe-command', { ...recipe, brixTarget: 20 })).toMatch(/brixTarget/);
    const { messageId: _m, ...noId } = recipe;
    expect(validateMessage('recipe-command', noId)).toMatch(/messageId/);
  });

  it('rejects unknown fields', () => {
    expect(validateMessage('recipe-command', { ...recipe, extra: 1 })).toMatch(/additional/);
  });

  it('checks formats', () => {
    expect(validateMessage('recipe-command', { ...recipe, messageId: 'x' })).toMatch(/uuid/);
  });
});
