import { FastifyInstance } from 'fastify';

export async function registerOnboardingRoutes(app: FastifyInstance) {
  app.get('/onboarding/questions', { preHandler: [app.authenticate] }, async () => {
    return {
      ok: true,
      sections: ['identity', 'birth', 'goals', 'consent']
    };
  });

  app.post('/onboarding/answers', { preHandler: [app.authenticate] }, async (req) => {
    return { ok: true, saved: true, payload: req.body };
  });
}
