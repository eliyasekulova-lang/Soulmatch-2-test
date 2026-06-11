import { FastifyInstance } from 'fastify';

export async function registerAdminRoutes(app: FastifyInstance) {
  app.get('/v1/admin/safety/audit', { preHandler: [app.authenticate] }, async () => {
    return { ok: true, items: [] };
  });

  app.get('/v1/admin/weights', { preHandler: [app.authenticate] }, async () => {
    return { ok: true, weights: {} };
  });

  app.put('/v1/admin/weights', { preHandler: [app.authenticate] }, async (req) => {
    return { ok: true, updated: req.body };
  });

  app.get('/v1/admin/reports', { preHandler: [app.authenticate] }, async () => {
    return { ok: true, reports: [] };
  });

  app.post('/v1/admin/reports/:id/actions', { preHandler: [app.authenticate] }, async (req) => {
    return { ok: true, reportId: (req.params as any).id, actionApplied: true };
  });

  app.post('/v1/admin/users/:id/suspend', { preHandler: [app.authenticate] }, async (req) => {
    return { ok: true, userId: (req.params as any).id, status: 'suspended' };
  });

  app.post('/v1/admin/users/:id/ban', { preHandler: [app.authenticate] }, async (req) => {
    return { ok: true, userId: (req.params as any).id, status: 'banned' };
  });

  app.get('/v1/admin/audit', { preHandler: [app.authenticate] }, async () => {
    return { ok: true, events: [] };
  });
}
