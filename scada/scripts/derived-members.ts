// Hand-written UDT members that are not Sparkplug metrics: state text, the stop-reason timer
// (SCA-30) and the line's "a reason is needed" summary. Times are sim time (EDG-06).
import { plcIoDoc } from '@vbp/contracts';
import type { TagJson } from './tag-json.js';

export const LINE_PATH = '[default]Delft/Packaging/Line1/Line';
const SIM_TIME = `${LINE_PATH}/SimTimeMs`;
const EXECUTE = 6;
/** A machine's own stops need an operator reason; Suspended (starved/blocked) does not. */
const OWN_STOPS = [2, 9, 11]; // Stopped, Aborted, Held
const REASON_AFTER_MS = 120_000;

function stateCase(): string {
  const states = Object.entries(plcIoDoc.enums.PackMLState ?? {});
  return `case({[.]State}, ${states.map(([n, name]) => `${n}, "${name}"`).join(', ')}, "Unknown")`;
}

/** Tag-change script on State: remember the sim time when the machine stops running. */
export const STATE_CHANGE_SCRIPT = [
  '\t# Generated (scada/scripts/derived-members.ts): start the stop-reason timer (SCA-30).',
  `\tif currentValue.value == ${EXECUTE}:`,
  '\t\treturn',
  `\tif not initialChange and previousValue.value != ${EXECUTE}:`,
  '\t\treturn',
  '\tbase = str(tagPath).rsplit("/", 1)[0]',
  `\tsim = system.tag.readBlocking(["${SIM_TIME}"])[0].value`,
  '\tsystem.tag.writeBlocking([base + "/NotRunningSinceMs"], [sim])',
].join('\n');

export function packmlDerivedMembers(): TagJson[] {
  const ownStop = OWN_STOPS.map((s) => `{[.]State} = ${s}`).join(' || ');
  return [
    {
      name: 'StateText',
      tagType: 'AtomicTag',
      dataType: 'String',
      valueSource: 'expr',
      expression: stateCase(),
    },
    {
      name: 'NotRunningSinceMs',
      tagType: 'AtomicTag',
      dataType: 'Int8',
      valueSource: 'memory',
      value: 0,
    },
    {
      name: 'ReasonNeeded',
      tagType: 'AtomicTag',
      dataType: 'Boolean',
      valueSource: 'expr',
      expression:
        `(${ownStop}) && {[.]StopReason} < 100 && {[.]NotRunningSinceMs} > 0` +
        ` && toInt64({${SIM_TIME}}) - {[.]NotRunningSinceMs} > ${REASON_AFTER_MS}`,
    },
  ];
}

/** On the line: true while any machine waits for an operator stop reason. */
export function lineDerivedMembers(machinePaths: string[]): TagJson[] {
  return [
    {
      name: 'AnyReasonNeeded',
      tagType: 'AtomicTag',
      dataType: 'Boolean',
      valueSource: 'expr',
      expression: machinePaths.map((p) => `{${p}/ReasonNeeded}`).join(' || '),
    },
  ];
}

/** Alarm event script: an ack in Ignition acknowledges the same alarm id in the PLC. */
export function alarmAckScript(alarmId: number): string {
  return [
    '\t# Generated: acknowledge this alarm in the PLC too (AlarmAck DCMD via the edge bridge).',
    `\tsystem.tag.writeBlocking(["${LINE_PATH}/AlarmAck"], [${alarmId}])`,
  ].join('\n');
}
