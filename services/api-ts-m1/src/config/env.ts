import 'dotenv/config';
import { z } from 'zod';

const Env = z.object({
  NODE_ENV: z.enum(['development', 'test', 'staging', 'production']).default('development'),
  PORT: z.coerce.number().default(8010),
  DATABASE_URL: z.string().min(1),
  JWT_SECRET: z.string().min(16),
  JWT_ACCESS_MINUTES: z.coerce.number().default(30),
  CORS_ALLOW_ORIGINS: z.string().default('http://localhost:3000')
});

export const env = Env.parse(process.env);
export const corsOrigins = env.CORS_ALLOW_ORIGINS.split(',').map((x) => x.trim());
