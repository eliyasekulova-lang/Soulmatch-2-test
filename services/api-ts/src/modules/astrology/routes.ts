import { FastifyInstance } from 'fastify';
import { z } from 'zod';

const NatalSchema = z.object({ userId: z.string() });
const SynastrySchema = z.object({ userId: z.string(), targetUserId: z.string(), mode: z.enum(['romance', 'friendship']) });

export async function registerAstrologyRoutes(app: FastifyInstance) {
  app.post('/v1/astrology/natal', { preHandler: [app.authenticate] }, async (req) => {
    const body = NatalSchema.parse(req.body);
    return { ok: true, userId: body.userId, computedAt: new Date().toISOString() };
  });

  app.post('/v1/astrology/synastry', { preHandler: [app.authenticate] }, async (req) => {
    const body = SynastrySchema.parse(req.body);
    return { ok: true, userId: body.userId, targetUserId: body.targetUserId, mode: body.mode, astrologyScore: 0.73 };
  });
}
