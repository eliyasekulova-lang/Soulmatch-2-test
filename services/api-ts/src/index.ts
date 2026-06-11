import Fastify from 'fastify';
import cors from '@fastify/cors';
import helmet from '@fastify/helmet';
import rateLimit from '@fastify/rate-limit';
import swagger from '@fastify/swagger';
import swaggerUi from '@fastify/swagger-ui';

import { env, corsOrigins } from './config/env.js';
import authPlugin from './plugins/auth.js';
import { registerAuthRoutes } from './modules/auth/routes.js';
import { registerProfileRoutes } from './modules/profile/routes.js';
import { registerAstrologyRoutes } from './modules/astrology/routes.js';
import { registerOnboardingRoutes } from './modules/onboarding/routes.js';
import { registerPolicyConsentRoutes } from './modules/onboarding/policyConsentRoutes.js';
import { registerBehaviorRoutes } from './modules/behavior/routes.js';
import { registerMatchRoutes } from './modules/matches/routes.js';
import { registerMessagingRoutes } from './modules/messaging/routes.js';
import { registerMediaRoutes } from './modules/media/routes.js';
import { registerOpenersRoutes } from './modules/openers/routes.js';
import { registerAdvisorRoutes } from './modules/advisor/routes.js';
import { registerSafetyRoutes } from './modules/safety/routes.js';
import { registerRightsRoutes } from './modules/safety/rightsRoutes.js';
import { registerAdminRoutes } from './modules/admin/routes.js';
import { startWorkers } from './jobs/queues.js';

export async function buildApp() {
  const app = Fastify({ logger: true });

  await app.register(cors, { origin: corsOrigins });
  await app.register(helmet);
  await app.register(rateLimit, { max: 120, timeWindow: '1 minute' });
  await app.register(swagger, {
    openapi: {
      info: { title: 'SoulMatch API', version: '1.0.0' }
    }
  });
  await app.register(swaggerUi, { routePrefix: '/docs' });
  await app.register(authPlugin);

  await registerAuthRoutes(app);
  await registerProfileRoutes(app);
  await registerAstrologyRoutes(app);
  await registerOnboardingRoutes(app);
  await registerPolicyConsentRoutes(app);
  await registerBehaviorRoutes(app);
  await registerMatchRoutes(app);
  await registerMessagingRoutes(app);
  await registerMediaRoutes(app);
  await registerOpenersRoutes(app);
  await registerAdvisorRoutes(app);
  await registerSafetyRoutes(app);
  await registerRightsRoutes(app);
  await registerAdminRoutes(app);

  app.get('/health', async () => ({ status: 'ok' }));
  app.get('/', async () => ({ name: 'SoulMatch API', version: '1.0.0' }));

  return app;
}

if (process.env.NODE_ENV !== 'test') {
  const app = await buildApp();
  startWorkers();
  await app.listen({ host: '0.0.0.0', port: env.PORT });
}
