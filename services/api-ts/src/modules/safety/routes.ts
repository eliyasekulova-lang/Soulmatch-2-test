import { FastifyInstance } from 'fastify';
import { z } from 'zod';

const ReportSchema = z.object({ targetUserId: z.string(), conversationId: z.string().optional(), reason: z.string().min(2) });
const BlockSchema = z.object({ targetUserId: z.string().min(3) });

export async function registerSafetyRoutes(app: FastifyInstance) {
  app.post('/v1/reports', { preHandler: [app.authenticate] }, async (req) => {
    const b = ReportSchema.parse(req.body);
    return { ok: true, reportId: `rpt_${Date.now()}`, targetUserId: b.targetUserId };
  });

  app.post('/v1/block', { preHandler: [app.authenticate] }, async (req) => {
    const b = BlockSchema.parse(req.body);
    return { ok: true, blocked: b.targetUserId };
  });

  app.post('/v1/blocks', { preHandler: [app.authenticate] }, async (req) => {
    const b = BlockSchema.parse(req.body);
    return { ok: true, blocked: b.targetUserId };
  });

  app.delete('/v1/blocks/:blockedUserId', { preHandler: [app.authenticate] }, async (req) => {
    return { ok: true, unblocked: (req.params as any).blockedUserId };
  });

  app.get('/v1/safety/tips', { preHandler: [app.authenticate] }, async () => {
    return {
      ok: true,
      tips: [
        'Avoid sharing phone/address early.',
        'Take your time before sending money or personal info.',
        'Use block+report immediately if anything feels unsafe.'
      ]
    };
  });
}
