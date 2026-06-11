import Fastify from 'fastify';
import cors from '@fastify/cors';
import helmet from '@fastify/helmet';
import rateLimit from '@fastify/rate-limit';

import { env, corsOrigins } from './config/env.js';
import authPlugin from './plugins/auth.js';
import { registerAuthRoutes } from './modules/auth/routes.js';
import { registerProfileRoutes } from './modules/profile/routes.js';
import { registerOnboardingRoutes } from './modules/onboarding/routes.js';
import { registerEventRoutes } from './modules/events/routes.js';

export async function buildApp() {
  const app = Fastify({ logger: true });

  await app.register(cors, { origin: corsOrigins });
  await app.register(helmet);
  await app.register(rateLimit, { max: 120, timeWindow: '1 minute' });
  await app.register(authPlugin);

  await registerAuthRoutes(app);
  await registerProfileRoutes(app);
  await registerOnboardingRoutes(app);
  await registerEventRoutes(app);

  app.get('/health', async () => ({ status: 'ok', milestone: 'M1' }));
  return app;
}

if (process.env.NODE_ENV !== 'test') {
  const app = await buildApp();
  await app.listen({ host: '0.0.0.0', port: env.PORT });
}
