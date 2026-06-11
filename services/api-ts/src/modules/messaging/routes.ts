import { FastifyInstance } from 'fastify';
import { z } from 'zod';

const CreateConv = z.object({ targetUserId: z.string().min(3) });
const PostMessage = z.object({ conversationId: z.string(), text: z.string().min(1), clientMessageId: z.string().optional() });

export async function registerMessagingRoutes(app: FastifyInstance) {
  app.post('/v1/conversations', { preHandler: [app.authenticate] }, async (req) => {
    const b = CreateConv.parse(req.body);
    return { ok: true, conversationId: `cnv_${Date.now()}`, targetUserId: b.targetUserId };
  });

  app.get('/v1/conversations', { preHandler: [app.authenticate] }, async () => {
    return { ok: true, conversations: [] };
  });

  app.post('/v1/messages', { preHandler: [app.authenticate] }, async (req) => {
    const b = PostMessage.parse(req.body);
    return { ok: true, messageId: `msg_${Date.now()}`, conversationId: b.conversationId, hiddenBySafety: false };
  });

  app.get('/v1/messages', { preHandler: [app.authenticate] }, async (req: any) => {
    const q = req.query as any;
    return { ok: true, conversationId: q.conversationId, messages: [], nextCursor: null };
  });
}
