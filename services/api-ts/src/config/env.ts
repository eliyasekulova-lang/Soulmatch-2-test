import 'dotenv/config';
import { z } from 'zod';

const EnvSchema = z.object({
  NODE_ENV: z.enum(['development', 'test', 'staging', 'production']).default('development'),
  PORT: z.coerce.number().default(8001),
  DATABASE_URL: z.string().min(1),
  REDIS_URL: z.string().min(1),
  JWT_SECRET: z.string().min(16),
  JWT_ACCESS_MINUTES: z.coerce.number().default(30),
  JWT_REFRESH_DAYS: z.coerce.number().default(30),
  CORS_ALLOW_ORIGINS: z.string().default('http://localhost:3000')
});

export const env = EnvSchema.parse(process.env);
export const corsOrigins = env.CORS_ALLOW_ORIGINS.split(',').map((x) => x.trim());
