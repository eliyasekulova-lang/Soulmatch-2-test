export type LayerScores = {
  astrologyChem: number;
  astrologyStab: number;
  psychChem: number;
  psychStab: number;
  behaviorChem: number;
  behaviorStab: number;
  intent: number;
  alignment: number;
};

export type ScoreWeights = {
  wA: number; wP: number; wB: number; wI: number; wL: number;
  wA2: number; wP2: number; wB2: number; wI2: number; wL2: number;
};

export function clamp01(v: number): number {
  return Math.max(0, Math.min(1, v));
}

export function attractionScore(l: LayerScores, w: ScoreWeights): number {
  return clamp01((w.wA * l.astrologyChem) + (w.wP * l.psychChem) + (w.wB * l.behaviorChem) + (w.wI * l.intent) + (w.wL * l.alignment));
}

export function destinyScore(l: LayerScores, w: ScoreWeights): number {
  return clamp01((w.wA2 * l.astrologyStab) + (w.wP2 * l.psychStab) + (w.wB2 * l.behaviorStab) + (w.wI2 * l.intent) + (w.wL2 * l.alignment));
}
