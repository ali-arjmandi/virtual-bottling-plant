import { describe, expect, it } from 'vitest';
import { recipeWrites, nakName, NAK_BUSY } from './recipe-words.js';
import { recipeCommand } from './test-recipe.js';

describe('recipe words', () => {
  it('scales every recipe value into one contiguous write', () => {
    expect(recipeWrites(recipeCommand)).toEqual([
      { mw: 903, values: [7, 3, 1, 1150, 30, 162, 10050, 120, 220] },
    ]);
  });

  it('names Nak codes from the contract', () => {
    expect(nakName(1)).toBe('InExecute');
    expect(nakName(NAK_BUSY)).toBe('Busy');
  });
});
