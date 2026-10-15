import { describe, expect, it } from 'vitest';
import { aclTopic, jsonTopic, sparkplugTopic } from './uns-topics.js';

describe('UNS topics', () => {
  it('builds Sparkplug topics', () => {
    expect(sparkplugTopic('NBIRTH')).toBe('spBv1.0/DelftsSap/NBIRTH/Line1');
    expect(sparkplugTopic('DDATA', 'C501')).toBe('spBv1.0/DelftsSap/DDATA/Line1/C501');
  });

  it('builds ISA-95 JSON topics', () => {
    expect(jsonTopic('state', 'capper')).toBe('delftssap/delft/packaging/line1/capper/state');
    expect(jsonTopic('state')).toBe('delftssap/delft/packaging/line1/+/state');
    expect(jsonTopic('recipe_result')).toBe('delftssap/delft/packaging/line1/cmd/recipe/result');
  });

  it('expands json: entries in the ACL', () => {
    expect(aclTopic('json:batch')).toBe('delftssap/delft/process/line1/mixer/batch');
    expect(aclTopic('spBv1.0/#')).toBe('spBv1.0/#');
  });
});
