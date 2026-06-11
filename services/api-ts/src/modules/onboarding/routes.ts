import { FastifyInstance } from 'fastify';

export async function registerOnboardingRoutes(app: FastifyInstance) {
  app.get('/v1/onboarding/questions', { preHandler: [app.authenticate] }, async () => {
    return {
      ok: true,
      sections: ['ocean', 'attachment', 'love_language', 'communication_style', 'conflict_style', 'social_energy', 'values', 'lifestyle']
    };
  });

  app.post('/v1/onboarding/answers', { preHandler: [app.authenticate] }, async (req) => {
    return { ok: true, stored: true, answers: req.body };
  });
}
