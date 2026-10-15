// The subset of Ignition's tag JSON (export/import, system.tag.configure) the generator writes.
import type { SparkplugType } from '@vbp/contracts';

export type Binding = { bindType: 'parameter'; binding: string };

export type AlarmJson = {
  name: string;
  label: string;
  priority: 'Critical' | 'High' | 'Medium' | 'Low' | 'Diagnostic';
  mode: 'Equality';
  setpointA: number;
  ackMode: 'Manual';
  displayPath: Binding;
};

export type TagJson = {
  name: string;
  tagType: 'AtomicTag' | 'Folder' | 'UdtType' | 'UdtInstance';
  dataType?: string;
  valueSource?: 'reference' | 'memory' | 'expr';
  sourceTagPath?: Binding;
  expression?: string;
  value?: unknown;
  typeId?: string;
  parameters?: Record<string, { dataType: 'String' | 'Integer'; value: string | number | Binding }>;
  engUnit?: string;
  historyEnabled?: boolean;
  historyProvider?: string;
  alarms?: AlarmJson[];
  eventScripts?: { eventid: string; script: string }[];
  tags?: TagJson[];
};

/** Sparkplug type → Ignition data type. UInt32 counters go to Int8 so they never overflow. */
export const DATA_TYPES: Record<SparkplugType, string> = {
  Boolean: 'Boolean',
  Int32: 'Int4',
  UInt32: 'Int8',
  Double: 'Float8',
};

export const param = (binding: string): Binding => ({ bindType: 'parameter', binding });

/** Puts `tag` at `path` (`Alarms/C501_Jam/Active`) under `root`, creating folders on the way. */
export function placeAt(root: TagJson[], path: string, tag: Omit<TagJson, 'name'>): void {
  const parts = path.split('/');
  let level = root;
  for (const folder of parts.slice(0, -1)) {
    let node = level.find((t) => t.name === folder && t.tagType === 'Folder');
    if (!node) {
      node = { name: folder, tagType: 'Folder', tags: [] };
      level.push(node);
    }
    level = node.tags!;
  }
  level.push({ name: parts[parts.length - 1]!, ...tag });
}
