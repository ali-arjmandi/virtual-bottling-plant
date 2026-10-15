// Shared fixture for the recipe specs: a valid WO-1042 recipe v3 command.
import type { RecipeCommand } from '@vbp/contracts';

export const recipeCommand: RecipeCommand = {
  ts: '2026-10-05T06:00:00.000Z',
  source: 'mes-api',
  schemaVersion: '1.0',
  messageId: '6f1c7a52-3f6e-4c39-9f43-0d1f1d2b6a11',
  workOrderNo: 'WO-1042',
  recipeId: 7,
  recipeVersion: 3,
  productCode: 1,
  brixTarget: 11.5,
  brixTol: 0.3,
  concRatio: 0.162,
  fillTargetG: 1005,
  lineSpeed: 120,
  capTorque: 2.2,
};
