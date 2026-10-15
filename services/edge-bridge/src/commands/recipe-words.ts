// RecipeCommand fields → plc-io recipe words (%MW903–911). Field names are the word names in
// camelCase (`brixTarget` → `BrixTarget`); values are scaled to integers as the contract says.
import { plcIoDoc, type RecipeCommand } from '@vbp/contracts';

export type WordWrite = { mw: number; values: number[] };

const recipe = plcIoDoc.recipe;
const word = (name: string) => {
  const w = [...recipe.request, ...recipe.response].find((x) => x.name === name);
  if (!w) throw new Error(`plc-io recipe: no word ${name}`);
  return w;
};

export const RECIPE_REQ_MW = word('Recipe_Req').mw;
export const RECIPE_ACK_MW = word('Recipe_Ack').mw;
export const RECIPE_NAK_MW = word('Recipe_Nak').mw;
export const RECIPE_TIMEOUT_MS = recipe.timeout_s * 1000;

const valueWords = recipe.request.filter((w) => w.name !== 'Recipe_Req');

function fieldName(wordName: string): keyof RecipeCommand {
  return (wordName[0]!.toLowerCase() + wordName.slice(1)) as keyof RecipeCommand;
}

/** Recipe values as the fewest contiguous %MW writes. */
export function recipeWrites(cmd: RecipeCommand): WordWrite[] {
  const words = valueWords
    .map((w) => {
      const value = cmd[fieldName(w.name)];
      if (typeof value !== 'number') throw new Error(`recipe field ${fieldName(w.name)} missing`);
      return { mw: w.mw, value: Math.round(value * (w.scale ?? 1)) };
    })
    .sort((a, b) => a.mw - b.mw);
  const writes: WordWrite[] = [];
  for (const w of words) {
    const last = writes[writes.length - 1];
    if (last && last.mw + last.values.length === w.mw) last.values.push(w.value);
    else writes.push({ mw: w.mw, values: [w.value] });
  }
  return writes;
}

export function nakName(code: number): string {
  return plcIoDoc.enums.RecipeNak?.[String(code)] ?? `Nak${code}`;
}

/** The PLC's Busy code, also used when the bridge is mid-handshake. */
export const NAK_BUSY = Number(
  Object.entries(plcIoDoc.enums.RecipeNak ?? {}).find(([, n]) => n === 'Busy')?.[0] ?? 8,
);
