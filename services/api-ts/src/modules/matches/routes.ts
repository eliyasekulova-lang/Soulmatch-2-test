import { FastifyInstance } from 'fastify';
import { attractionScore, destinyScore, LayerScores, ScoreWeights } from './scoring.js';

const defaultWeights: ScoreWeights = {
  wA: 0.24, wP: 0.26, wB: 0.18, wI: 0.16, wL: 0.16,
  wA2: 0.20, wP2: 0.28, wB2: 0.22, wI2: 0.15, wL2: 0.15
};

export async function registerMatchRoutes(app: FastifyInstance) {
  app.get('/v1/matches', { preHandler: [app.authenticate] }, async (req: any) => {
    const q = req.query as any;
    const mode = q.mode === 'destiny' ? 'destiny' : 'attraction';
    const type = q.type === 'friendship' ? 'friendship' : 'romance';

    const layer: LayerScores = {
      astrologyChem: 0.76, astrologyStab: 0.68,
      psychChem: 0.72, psychStab: 0.74,
      behaviorChem: 0.61, behaviorStab: 0.66,
      intent: 0.79, alignment: 0.70
    };

    const attraction = attractionScore(layer, defaultWeights);
    const destiny = destinyScore(layer, defaultWeights);

    return {
      ok: true,
      mode,
      type,
      matches: [{
        targetUserId: 'demo_target_1',
        totalAttractionScore: attraction,
        totalDestinyScore: destiny,
        explanationTokens: ['Strong communication fit', 'Aligned intent', 'Supportive astrology chemistry']
      }]
    };
  });

  app.get('/v1/matches/:id/explain', { preHandler: [app.authenticate] }, async () => {
    return {
      ok: true,
      reasons: [
        'Astrology: supportive Venus-Mars dynamics for this mode.',
        'Psychology: communication preference alignment is high.',
        'Behavior: healthy reciprocity signal trend.',
        'Life alignment: schedule and values overlap is strong.'
      ],
      watchouts: ['Clarify expectations early and keep pacing mutual.']
    };
  });

  app.get('/v1/matches/:id/prediction', { preHandler: [app.authenticate] }, async () => {
    return {
      ok: true,
      intensity: 0.71,
      stability: 0.69,
      conflictRisk: 0.32,
      growthPotential: 0.77,
      disclaimer: 'Guidance only, not deterministic.'
    };
  });
}
