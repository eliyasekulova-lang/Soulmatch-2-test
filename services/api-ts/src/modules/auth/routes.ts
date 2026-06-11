import { FastifyInstance } from 'fastify';
import { z } from 'zod';
import crypto from 'node:crypto';

const SignupSchema = z.object({
  email: z.string().email(),
  password: z.string().min(8),
  birthDate: z.string().regex(/^\d{4}-\d{2}-\d{2}$/)
});

const LoginSchema = z.object({
  email: z.string().email(),
  password: z.string().min(8)
});

export async function registerAuthRoutes(app: FastifyInstance) {
  app.post('/v1/auth/signup', async (req, reply) => {
    const body = SignupSchema.parse(req.body);
    const userId = `usr_${crypto.randomUUID().replace(/-/g, '').slice(0, 16)}`;
    const token = await reply.jwtSign({ sub: userId, role: 'user' });
    return { ok: true, userId, accessToken: token, email: body.email };
  });

  app.post('/v1/auth/login', async (req, reply) => {
    const body = LoginSchema.parse(req.body);
    const token = await reply.jwtSign({ sub: `usr_login_${Date.now()}`, role: 'user' });
    return { ok: true, accessToken: token, email: body.email };
  });
}
