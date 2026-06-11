import { FastifyInstance } from 'fastify';
import { z } from 'zod';

const ProfileSchema = z.object({
  legalName: z.string().min(1),
  modePrefs: z.object({ romance: z.boolean(), friendship: z.boolean() }),
  intentPrefs: z.object({ seriousness: z.number().min(0).max(1) })
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
  app.get('/profile', { preHandler: [app.authenticate] }, async (req: any) => {
    return { ok: true, userId: req.user.sub, profile: null };
  });

  app.put('/profile', { preHandler: [app.authenticate] }, async (req: any) => {
    const body = ProfileSchema.parse(req.body);
    return { ok: true, userId: req.user.sub, updated: body };
  });

  app.post('/profile/birthdata', { preHandler: [app.authenticate] }, async (req: any) => {
    const body = BirthDataSchema.parse(req.body);
    return { ok: true, userId: req.user.sub, birthData: body };
  });
}
