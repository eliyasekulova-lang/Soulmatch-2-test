import { FastifyInstance } from 'fastify';
import { z } from 'zod';

const ConsentSchema = z.object({
  policyKey: z.string(),
  policyVersion: z.string(),
  locale: z.string(),
  country: z.string(),
  appVersion: z.string().optional(),
  granted: z.boolean().default(true)
});

export async function registerPolicyConsentRoutes(app: FastifyInstance) {
  app.get('/v1/policies', { preHandler: [app.authenticate] }, async () => ({ ok: true, policies: [] }));
  app.get('/v1/policies/:key', { preHandler: [app.authenticate] }, async (req) => ({ ok: true, key: (req.params as any).key }));
  app.get('/v1/policies/:key/versions/:version', { preHandler: [app.authenticate] }, async (req) => ({ ok: true, key: (req.params as any).key, version: (req.params as any).version }));

  app.post('/v1/consents', { preHandler: [app.authenticate] }, async (req) => {
    const b = ConsentSchema.parse(req.body);
    return { ok: true, consentId: `cons_${Date.now()}`, capturedAt: new Date().toISOString(), ...b };
  });

  app.get('/v1/consents/history', { preHandler: [app.authenticate] }, async () => ({ ok: true, history: [] }));
}
