import { FastifyInstance } from 'fastify';
import { z } from 'zod';

const PresignSchema = z.object({ mimeType: z.string(), mediaType: z.enum(['image', 'video']) });
const AttachSchema = z.object({ conversationId: z.string(), messageId: z.string().optional() });

export async function registerMediaRoutes(app: FastifyInstance) {
  app.post('/v1/media/presign', { preHandler: [app.authenticate] }, async (req) => {
    const b = PresignSchema.parse(req.body);
    const mediaId = `med_${Date.now()}`;
    return { ok: true, mediaId, uploadUrl: `http://localhost:9000/${mediaId}`, mimeType: b.mimeType };
  });

  app.post('/v1/media/:id/attach', { preHandler: [app.authenticate] }, async (req) => {
    const b = AttachSchema.parse(req.body);
    return { ok: true, mediaId: (req.params as any).id, attachedTo: b.conversationId };
  });

  app.get('/v1/media/:id', { preHandler: [app.authenticate] }, async (req) => {
    return { ok: true, mediaId: (req.params as any).id, downloadUrl: `http://localhost:9000/${(req.params as any).id}` };
  });
}
