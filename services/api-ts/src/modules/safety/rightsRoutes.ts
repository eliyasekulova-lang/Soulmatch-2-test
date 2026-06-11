import { FastifyInstance } from 'fastify';
import { z } from 'zod';

const RightsSchema = z.object({ reason: z.string().optional(), scope: z.array(z.string()).optional() });

export async function registerRightsRoutes(app: FastifyInstance) {
  app.post('/v1/rights/export', { preHandler: [app.authenticate] }, async (req) => {
    const b = RightsSchema.parse(req.body ?? {});
    return { ok: true, requestId: `rr_export_${Date.now()}`, status: 'queued', ...b };
  });

  app.post('/v1/rights/delete', { preHandler: [app.authenticate] }, async (req) => {
    const b = RightsSchema.parse(req.body ?? {});
    return { ok: true, requestId: `rr_delete_${Date.now()}`, status: 'queued', ...b };
  });

  app.get('/v1/rights/requests', { preHandler: [app.authenticate] }, async () => {
    return { ok: true, requests: [] };
  });
}
