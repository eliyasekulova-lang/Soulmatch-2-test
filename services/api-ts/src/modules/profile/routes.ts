import { FastifyInstance } from 'fastify';
import { z } from 'zod';

const ProfilePutSchema = z.object({
  legalName: z.string().min(1),
  modePrefs: z.object({ romance: z.boolean(), friendship: z.boolean() }).optional(),
  intentPrefs: z.object({ seriousness: z.number().min(0).max(1) }).optional()
});

const BirthDataSchema = z.object({
  date: z.string(),
  time: z.string(),
  city: z.string(),
  country: z.string(),
  lat: z.number(),
  lng: z.number(),
  timezone: z.string()
});

export async function registerProfileRoutes(app: FastifyInstance) {
  app.get('/v1/me', { preHandler: [app.authenticate] }, async (req: any) => {
    return { ok: true, userId: req.user.sub, legalName: 'Demo User' };
  });

  app.get('/v1/profile', { preHandler: [app.authenticate] }, async (req: any) => {
    return { ok: true, userId: req.user.sub, profile: {} };
  });

  app.put('/v1/profile', { preHandler: [app.authenticate] }, async (req: any) => {
    const body = ProfilePutSchema.parse(req.body);
    return { ok: true, userId: req.user.sub, updated: body };
  });

  app.post('/v1/profile/birthdata', { preHandler: [app.authenticate] }, async (req: any) => {
    const body = BirthDataSchema.parse(req.body);
    return { ok: true, userId: req.user.sub, birthData: body };
  });
}
