// Topic names of the UNS (contracts.md §3), built from topics.yaml.
import { topicsDoc, type TopicsDoc } from './contract-types.js';

export type SparkplugMessageType =
  | 'NBIRTH' | 'NDEATH' | 'NDATA' | 'NCMD' | 'DBIRTH' | 'DDEATH' | 'DDATA' | 'DCMD';

export type JsonTopicName = keyof TopicsDoc['json']['topics'] & string;

/** spBv1.0/DelftsSap/{type}/Line1[/{device}] */
export function sparkplugTopic(type: SparkplugMessageType, device?: string, uns = topicsDoc): string {
  const { namespace, group, node } = uns.sparkplug;
  const base = `${namespace}/${group}/${type}/${node}`;
  return device ? `${base}/${device}` : base;
}

/** Full JSON topic; `{cell}` is filled from `cell`, or left as the MQTT wildcard `+`. */
export function jsonTopic(name: JsonTopicName, cell?: string, uns = topicsDoc): string {
  const spec = uns.json.topics[name];
  if (!spec) throw new Error(`unknown JSON topic ${name}`);
  return `${uns.json.root}/${spec.path.replace('{cell}', cell ?? '+')}`;
}

/** Expands `json:<name>` entries of the ACL table; other entries are MQTT filters as they are. */
export function aclTopic(entry: string, uns = topicsDoc): string {
  return entry.startsWith('json:') ? jsonTopic(entry.slice(5), undefined, uns) : entry;
}
