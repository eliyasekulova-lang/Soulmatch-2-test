import { FastifyInstance } from 'fastify';

export async function registerBehaviorRoutes(app: FastifyInstance) {
  app.post('/v1/events', { preHandler: [app.authenticate] }, async (req: any) => {
    return { ok: true, userId: req.user.sub, accepted: true };
  });

  app.get('/v1/profile/behavior', { preHandler: [app.authenticate] }, async (req: any) => {
    return { ok: true, userId: req.user.sub, behaviorProfile: { updatedAt: new Date().toISOString() } };
  });
}
