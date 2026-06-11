import { describe, expect, it } from 'vitest';
import { attractionScore, destinyScore } from '../../src/modules/matches/scoring.js';

describe('scoring', () => {
  it('computes bounded attraction and destiny scores', () => {
    const layer = {
      astrologyChem: 0.7, astrologyStab: 0.6,
      psychChem: 0.8, psychStab: 0.7,
      behaviorChem: 0.5, behaviorStab: 0.65,
      intent: 0.9, alignment: 0.75
    };
    const weights = {
      wA: 0.24, wP: 0.26, wB: 0.18, wI: 0.16, wL: 0.16,
      wA2: 0.20, wP2: 0.28, wB2: 0.22, wI2: 0.15, wL2: 0.15
    };

    const a = attractionScore(layer, weights);
    const d = destinyScore(layer, weights);
    expect(a).toBeGreaterThan(0);
    expect(a).toBeLessThanOrEqual(1);
    expect(d).toBeGreaterThan(0);
    expect(d).toBeLessThanOrEqual(1);
  });
});
