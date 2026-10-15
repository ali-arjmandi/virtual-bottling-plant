// Writes scada/tags/ from /contracts: one JSON file per UDT and the Line 1 instances, in
// Ignition's tag JSON (importable with system.tag.configure). Run: pnpm gen:scada
// CI fails if the committed files differ.
import { mkdirSync, readdirSync, rmSync, writeFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { buildInstances, buildUdts } from './udt-model.js';

const tagsDir = resolve(import.meta.dirname, '../tags');
const udtDir = join(tagsDir, 'udts');
const json = (value: unknown) => `${JSON.stringify(value, null, 2)}\n`;

mkdirSync(udtDir, { recursive: true });
mkdirSync(join(tagsDir, 'instances'), { recursive: true });
for (const stale of readdirSync(udtDir)) rmSync(join(udtDir, stale));

for (const type of buildUdts()) {
  writeFileSync(join(udtDir, `${type.name}.json`), json(type));
  console.log(`wrote tags/udts/${type.name}.json`);
}
writeFileSync(
  join(tagsDir, 'instances/line1.json'),
  json({ name: '', tagType: 'Folder', tags: buildInstances() }),
);
console.log('wrote tags/instances/line1.json');
