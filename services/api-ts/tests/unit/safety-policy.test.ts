import { describe, expect, it } from 'vitest';
import { detectReasonCodes } from '../../src/modules/safety/detectors.js';
import { actionsForBand, riskBand } from '../../src/modules/safety/policyEngine.js';

describe('safety policy', () => {
  it('detects money and isolation cues', () => {
    const codes = detectReasonCodes('Only trust me and send money today.');
    expect(codes).toContain('MONEY_CUE');
    expect(codes).toContain('ISOLATION_CUE');
  });

  it('maps risk score to actions', () => {
    expect(riskBand(80)).toBe('critical');
    expect(actionsForBand('critical')).toContain('shadow_throttle');
  });
});
