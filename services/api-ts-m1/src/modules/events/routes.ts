import { FastifyInstance } from 'fastify';
import { z } from 'zod';

const EventSchema = z.object({
  eventName: z.string().min(2),
  eventPayload: z.record(z.any()).default({})
});

export async function registerEventRoutes(app: FastifyInstance) {
  app.post('/events', { preHandler: [app.authenticate] }, async (req: any) => {
    const body = EventSchema.parse(req.body);
    return { ok: true, userId: req.user.sub, accepted: true, event: body.eventName };
  });
}
