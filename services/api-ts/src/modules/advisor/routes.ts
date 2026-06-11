import { FastifyInstance } from 'fastify';
import { z } from 'zod';
import { isBlockedAdvisorPrompt } from './policy.js';

const AdvisorSchema = z.object({ prompt: z.string().min(3).max(1500) });

export async function registerAdvisorRoutes(app: FastifyInstance) {
  app.post('/v1/advisor', { preHandler: [app.authenticate] }, async (req) => {
    const b = AdvisorSchema.parse(req.body);
    if (isBlockedAdvisorPrompt(b.prompt)) {
      return {
        ok: false,
        blocked: true,
        message: 'This assistant supports forward-looking guidance. Try: How can I set boundaries early in new conversations?'
      };
    }
    return { ok: true, blocked: false, guidance: 'Use direct, kind communication and confirm boundaries early.' };
  });
}
