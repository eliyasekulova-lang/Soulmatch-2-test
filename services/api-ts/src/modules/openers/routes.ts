import { FastifyInstance } from 'fastify';

export async function registerOpenersRoutes(app: FastifyInstance) {
  app.get('/v1/matches/:id/openers', { preHandler: [app.authenticate] }, async (req: any) => {
    const tone = (req.query as any).tone ?? 'thoughtful';
    return {
      ok: true,
      label: 'Opening message suggestions',
      tone,
      suggestions: [
        { text: 'Hey, your profile stood out — what are you currently excited about?', rationale: 'Open-ended, warm start.' },
        { text: 'I noticed we both value direct communication. Want to start with one fun fact each?', rationale: 'Signals alignment quickly.' }
      ]
    };
  });
}
