// Ajv validators for every message schema in contracts/schemas/.
import { Ajv2020, type ValidateFunction } from 'ajv/dist/2020.js';
import addFormatsModule from 'ajv-formats';
import { schemas } from './generated/schemas.js';

export type SchemaName = keyof typeof schemas extends `${infer N}.json` ? N : never;

// ajv-formats ships CommonJS; its default export is the plugin function.
const addFormats = addFormatsModule as unknown as (ajv: Ajv2020) => Ajv2020;

const ajv = new Ajv2020({ allErrors: true, strict: true });
addFormats(ajv);
for (const schema of Object.values(schemas)) ajv.addSchema(schema as object);

const cache = new Map<string, ValidateFunction>();

function validator(name: SchemaName): ValidateFunction {
  let fn = cache.get(name);
  if (!fn) {
    fn = ajv.getSchema(`${name}.json`);
    if (!fn) throw new Error(`no schema ${name}.json`);
    cache.set(name, fn);
  }
  return fn;
}

/** Returns null when valid, else a one-line description of the errors. */
export function validateMessage(name: SchemaName, data: unknown): string | null {
  const fn = validator(name);
  if (fn(data)) return null;
  return ajv.errorsText(fn.errors, { dataVar: name });
}
